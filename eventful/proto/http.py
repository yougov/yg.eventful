from eventful import MessageProtocol, Deferred

def parse_request_line(line):
	items = line.split(' ')
	items[0] = items[0].upper()
	if len(items) == 2:
		return tuple(items) + ('0.9',)
	items[2] = items[2].split('/')[-1].strip()
	return tuple(items)

class HttpHeaders:
	def __init__(self):
		self._headers = {}
		self.items = self._headers.items
		self.keys = self._headers.keys
		self.values = self._headers.values
		self.itervalues = self._headers.itervalues
		self.iteritems = self._headers.iteritems

	def add(self, k, v):
		self._headers.setdefault(k.lower(), []).append(str(v).strip())

	def remove(self, k):
		if k.lower() in self._headers:
			del self._headers[k.lower()]

	def format(self):
		s = []
		for h, vs in self._headers.iteritems():
			for v in vs:
				s.append('%s: %s' % (h.title(), v))
		return '\r\n'.join(s)

	def parse(self, rawInput):
		ws = ' \t'
		heads = {}
		curhead = None
		curbuf = []
		for line in rawInput.splitlines():
			if not line.strip():
				continue
			if line[0] in ws:
				curbuf.append(line.strip())
			else:
				if curhead:
					heads.setdefault(curhead, []).append(' '.join(curbuf))
				name, body = map(str.strip, line.split(':', 1))
				curhead = name.lower()
				curbuf = [body]
		if curhead:
			heads.setdefault(curhead, []).append(' '.join(curbuf))
		self._headers = heads

	def __contains__(self, k):
		return k.lower() in self._headers

	def __getitem__(self, k):
		return self._headers[k.lower()]

	def get(self, k, d=None):
		return self._headers.get(k.lower(), d)

	def __iter__(self):
		return self._headers

class HttpRequest:
	def __init__(self, cmd, url, version, id):
		self.cmd = cmd
		self.url = url
		self.version = version
		self.headers = None
		self.body = None
		self.id = id
		
class HttpProtocolError(Exception): pass	

class HttpServerProtocol(MessageProtocol):
	def on_init(self):
		MessageProtocol.on_init(self)
		self.set_readable(True)
		
		# Standard requests, with potential POST 
		self.add_signal_handler('http.request_line', self.on_req_line)
		self.add_signal_handler('http.headers', self.on_headers)
		self.add_signal_handler('http.body', self.on_body)
		
		# Chunked
		self.add_signal_handler('http.chunk_size', self.on_chunk_size)
		self.add_signal_handler('http.chunk_body', self.on_chunk_body)
		self.add_signal_handler('http.chunk_trailer', self.on_chunk_trailer)
		
		self.reset()
		self._req_id = 1
		self._waiting_responses = {}
		self._next_response = 1
		
	def reset(self):	
		self._req = None
		self.request_message('http.request_line', sentinel='\r\n')

	def get_handler_method(self, cmd):
		try:
			return getattr(self, 'on_HTTP_%s' % cmd)
		except AttributeError:
			return self.on_no_http_handler

	def on_req_line(self, ev, data):
		cmd, url, version = parse_request_line(data)	
		self._req = HttpRequest(cmd, url, version, self._req_id)
		self._req_id += 1
		self.request_message('http.headers', sentinel='\r\n\r\n')

	def check_expect(self, heads):
		if self._req.version >= '1.1' and heads.get('Expect') == ['100-continue']:
			self.write('HTTP/1.1 100 Continue\r\n\r\n')

	def on_headers(self, ev, data):
		heads = HttpHeaders()
		heads.parse(data)
		is_more = self.check_for_http_body(heads)
		self._req.headers = heads
		self.check_expect(heads)
		if not is_more:
			self.get_handler_method(self._req.cmd)(self._req)
			self.reset()

	def on_body(self, ev, data):
		self._req.body = data
		self.get_handler_method(self._req.cmd)(self._req)
		self.eatData(2) # trailing CRLF
		self.reset()

	def check_for_http_body(self, heads):
		if heads.get('Transfer-Encoding') == ['chunked']:
			self._chunks = []
			self.request_message('http.chunk_size', sentinel='\r\n')
			return True
		elif 'Content-Length' in heads:
			self.request_message('http.body', bytes=int(heads['Content-Length'][0]))
			return True
		return False

	def on_no_http_handler(self, req):
		msg = 'No such handler for HTTP command %s' % req.cmd
		heads = HttpHeaders()
		heads.add('Content-Type', 'text/plain')
		heads.add('Content-Length', len(msg))
		self.send_http_response(req, '501 Not Implemented', heads, msg)

	# "Chunked" transfer encoding states
	def on_chunk_size(self, ev, data):
		if ';' in data:
			# we don't support any chunk extensions
			data = data[:data.find(';')]
		size = int(data, 16)
		if size == 0:
			self.request_message('http.chunk_trailer', sentinel='\r\n')
		else:
			self.request_message('http.chunk_body', bytes=size)

	def on_chunk_body(self, ev, data):
		self._chunks.append(data)
		self.request_message('http.chunk_size', sentinel='\r\n')
		self.skip_input(2) # Get rid of trailing CRLF

	def on_chunk_trailer(self, ev, data):
		if not data.strip():
			# We've reached the end.. phew!
			data = ''.join(self._chunks)
			self._req.headers.add('Content-Length', len(data))
			self._req.headers.remove('Transfer-Encoding')
			self._req.body = data
			self._chunks = []
			self.get_handler_method(self._req.cmd)(self._req)
			self.reset()
		else:
			# Adding a header via the trailer...
			self._req.headers.add(*tuple(data.split(':', 1)))

	def send_http_response(self, req, code, heads, body):
		if req.id == self._next_response:
			self._send_http_response(req, code, heads, body)
			if self._waiting_responses:
				self._process_waiting_responses()
		else:
			self._waiting_responses[req.id] = (req, code, heads, body, None)
		
	def _send_http_response(self, req, code, heads, body, chunked=False):
		self.write(
'''HTTP/%s %s\r\n%s\r\n\r\n''' % (req.version, code, heads.format()))
		if body:
			self.write(body)
		if not chunked and (req.version < '1.1' or req.headers.get('Connection') == ['close']):
			self.close_cleanly()
		self._next_response += 1
		
	def start_chunked_response(self, req, code, heads):	
		if req.version < '1.1':
			raise HttpProtocolError, 'Cannot send a chunked response back to a < 1.1 client'
			
		if req.id == self._next_response:
			self._chunk_req = req
			self._send_http_response(req, code, heads, None, True)
			return self._add_chunk
		else:
			d = Deferred()
			self._waiting_responses[req.id] = (req, code, heads, None, d)
			return d
		
	def _process_waiting_responses(self):
		while self._next_response in self._waiting_responses:
			next = self._waiting_responses.pop(self._next_response)
			self._send_http_response(*next)
			if next[-1]:
				self._chunk_req = next[0]
				next[-1].callback(self._add_chunk)
				
	def _add_chunk(self, data, extra_headers=None):	
		if data == None:
			req = self._chunk_req
			self.write('0\r\n')
			if extra_headers:
				self.write(extra_headers.format() + '\r\n')
			self.write('\r\n')
			if req.headers.get('Connection') == ['close']:
				self.close_cleanly()
		else:
			self.write('%x\r\n%s\r\n' % (len(data), data))
