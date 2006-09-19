import sys

from eventful import MessageProtocol, Deferred, Client

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
		self.link()

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
	
	def link(self):
		self.items = self._headers.items
		self.keys = self._headers.keys
		self.values = self._headers.values
		self.itervalues = self._headers.itervalues
		self.iteritems = self._headers.iteritems

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
		self.link()

	def __contains__(self, k):
		return k.lower() in self._headers

	def __getitem__(self, k):
		return self._headers[k.lower()]

	def get(self, k, d=None):
		return self._headers.get(k.lower(), d)

	def __iter__(self):
		return self._headers

class HttpRequest:
	def __init__(self, cmd, url, version, id=None):
		self.cmd = cmd
		self.url = url
		self.version = version
		self.headers = None
		self.body = None
		self.id = id
		
	def format(self):	
		return '%s %s HTTP/%s' % (self.cmd, self.url, self.version)
		
class HttpProtocolError(Exception): pass	

class HttpCommon(MessageProtocol):
	def on_init(self):
		MessageProtocol.on_init(self)
		self.set_readable(True)
		
		self.add_signal_handler('http.headers', self.on_headers)
		self.add_signal_handler('http.body', self.on_body)
		
		# Chunked
		self.add_signal_handler('http.chunk_size', self.on_chunk_size)
		self.add_signal_handler('http.chunk_body', self.on_chunk_body)
		self.add_signal_handler('http.chunk_trailer', self.on_chunk_trailer)
		
	def on_headers(self, ev, data):
		heads = HttpHeaders()
		heads.parse(data)
		is_more = self.check_for_http_body(heads)
		self.check_expect(heads)
		if not is_more:
			self.message_in(heads, None)
		else:	
			self._headers = heads

	def on_body(self, ev, data):
		self.message_in(self._headers, data)
		
	def check_for_http_body(self, heads):
		if heads.get('Transfer-Encoding') == ['chunked']:
			self._chunks = []
			self.request_message('http.chunk_size', sentinel='\r\n')
			return True
		elif 'Content-Length' in heads:
			self.request_message('http.body', bytes=int(heads['Content-Length'][0]))
			return True
		return False

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
			self._headers.add('Content-Length', len(data))
			self._headers.remove('Transfer-Encoding')
			self._chunks = []
			self.message_in(self._headers, data)
		else:
			# Adding a header via the trailer...
			self._headers.add(*tuple(data.split(':', 1)))
			
	def check_expect(self, heads):	
		pass
	
	def _add_chunk(self, data, extra_headers=None):	
		if data == None:
			self.write('0\r\n')
			if extra_headers:
				self.write(extra_headers.format() + '\r\n')
			self.write('\r\n')
			self.chunks_done()
		else:
			self.write('%x\r\n%s\r\n' % (len(data), data))

class HttpServerProtocol(HttpCommon):
	def on_init(self):
		HttpCommon.on_init(self)
		self.add_signal_handler('http.request_line', self.on_req_line)
		self.reset()
		self._waiting_responses = {}
		self._req_id = 1
		self._next_response = 1
		
	def reset(self):	
		self._req = None
		self.request_message('http.request_line', sentinel='\r\n')

	def get_handler_method(self, cmd):
		try:
			return getattr(self, 'on_HTTP_%s' % cmd)
		except AttributeError:
			return self.on_no_http_handler
		
	def message_in(self, heads, body):
		self._req.headers = heads
		self._req.body = body
		self.get_handler_method(self._req.cmd)(self._req)
		self.reset()

	def on_req_line(self, ev, data):
		cmd, url, version = parse_request_line(data)	
		self._req = HttpRequest(cmd, url, version, self._req_id)
		self._req_id += 1
		self.request_message('http.headers', sentinel='\r\n\r\n')

	def send_http_response(self, req, code, heads, body):
		if req.id == self._next_response:
			self._send_http_response(req, code, heads, body)
			if self._waiting_responses:
				self._process_waiting_responses()
		else:
			self._waiting_responses[req.id] = (req, code, heads, body, None)
			
	def check_expect(self, heads):
		if self._req.version >= '1.1' and heads.get('Expect') == ['100-continue']:
			self.write('HTTP/1.1 100 Continue\r\n\r\n')
		
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
				
	def chunks_done(self):	
		req = self._chunk_req
		if req.headers.get('Connection') == ['close']:
			self.close_cleanly()
			
	def on_no_http_handler(self, req):
		msg = 'No such handler for HTTP command %s' % req.cmd
		heads = HttpHeaders()
		heads.add('Content-Type', 'text/plain')
		heads.add('Content-Length', len(msg))
		self.send_http_response(req, '501 Not Implemented', heads, msg)
			
class HttpResponse:
	def __init__(self, code, status, version):
		self.code = code
		self.status = status
		self.version = version
		self.headers = None
		
	def __str__(self):	
		def p():
			yield "HTTP/%s %s %s\n" % (self.version, self.code, self.status)
			yield "\nHeaders\n-------------\n"
			for h, v in self.headers.iteritems():
				yield "%s: %s\n" % (h, ','.join(v))
		return ''.join(list(p()))

def parse_response_line(line):	
	ver, code, status  = line.strip().split(' ', 2)
	ver = ver.split('/')[-1]
	code = int(code)
	return code, status, ver
		
class HttpClientProtocol(HttpCommon):
	def __init__(self, sock, remote_addr, version='1.1'):
		HttpCommon.__init__(self, sock, remote_addr)
		self._http_version = version
		self._callbacks = []
		self._closemark = False
		
	def on_init(self):	
		HttpCommon.on_init(self)
		self.add_signal_handler('http.response_line', self.on_response_line)
		self.reset()
		
	def reset(self):	
		self.request_message('http.response_line', sentinel='\r\n')
		self.resp = None
		
	def request(self, cmd, path, heads, body):	
		req = HttpRequest(cmd, path, self._http_version)
		self.write('%s\r\n%s\r\n\r\n' % (req.format(), heads.format()))
		if body:
			self.write(body)
		d = Deferred()	
		self._callbacks.append(d)
		return d
	
	def on_response_line(self, ev, data):
		self.resp = HttpResponse(*parse_response_line(data))
		self.request_message('http.headers', sentinel='\r\n\r\n')
	
	def message_in(self, headers, body):
		self.resp.headers = headers
		if body == None and headers.get('Connection') == ['close']:
			if self.closed:
				self.finish_message()
			else:	
				self.add_signal_handler('prot.disconnected', self.finish_message)
				self.request_message(bytes=sys.maxint)
		else:	
			d = self._callbacks.pop(0)
			d.callback((self.resp, body))
			self.reset()
		
	def finish_message(self, ev):	
		body = self.pop_buffer()
		d = self._callbacks.pop(0)
		d.callback((self.resp, body))
	
class HttpClient(Client):
	def __init__(self, version='1.1'):
		Client.__init__(self, HttpClientProtocol, version=version)