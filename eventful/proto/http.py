import dispatch

from eventful import AutoTerminatingProtocol

def parseRequestLine(line):
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
		for line in rawInput.split('\r\n'):
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
	def __init__(self, cmd, url, version):
		self.cmd = cmd
		self.url = url
		self.version = version
		self.headers = None
		self.body = None

class HttpServerProtocol(AutoTerminatingProtocol):
	ST_RLINE = 1
	ST_HEADS = 2
	ST_BODY_CLEN  = 3
	ST_CHUNK_SZ  = 4
	ST_CHUNK_DATA  = 5
	ST_CHUNK_TRAILER  = 6

	def onProtocolHandlerCreate(self):
		self.setReadable(True)
		self.setTerminator('\r\n')
		self._http_state = self.ST_RLINE
		self._req = None

	def getHandlerMethod(self, cmd):
		try:
			return getattr(self, 'on_HTTP_%s' % cmd)
		except AttributeError:
			return self.on_noHttpHandler

	@dispatch.generic()
	def onDataChunk(self, data):
		pass	

	@onDataChunk.when('self._http_state == self.ST_RLINE')
	def onReqLine(self, data):
		cmd, url, version = parseRequestLine(data)	
		self._req = HttpRequest(cmd, url, version)
		self._http_state = self.ST_HEADS
		self.setTerminator('\r\n\r\n')

	def checkExpect(self, heads):
		if self._req.version >= '1.1' and heads.get('Expect') == ['100-continue']:
			self.write('HTTP/1.1 100 Continue\r\n\r\n')

	@onDataChunk.when('self._http_state == self.ST_HEADS')
	def onHeaders(self, data):
		heads = HttpHeaders()
		heads.parse(data)
		nextState = self.checkForHttpBody(heads)
		self._req.headers = heads
		self.checkExpect(heads)
		if nextState is None:
			self.getHandlerMethod(self._req.cmd)(self._req)
			self.setTerminator('\r\n')
			self._http_state = self.ST_RLINE
		else:
			self._http_state = nextState

	@onDataChunk.when('self._http_state == self.ST_BODY_CLEN')
	def onEndBody(self, data):
		self._req.body = data
		self.getHandlerMethod(self._req.cmd)(self._req)
		self.setTerminator('\r\n')
		self._http_state = self.ST_RLINE
		self.eatData(2) # trailing CRLF

	def checkForHttpBody(self, heads):
		if heads.get('Transfer-Encoding') == ['chunked']:
			self.setTerminator('\r\n')
			self._chunks = []
			return self.ST_CHUNK_SZ

		elif 'Content-Length' in heads:
			self.setTerminator(int(heads['Content-Length'][0]))
			return self.ST_BODY_CLEN
		return None

	def on_noHttpHandler(self, req):
		msg = 'No such handler for HTTP command %s' % req.cmd
		heads = HttpHeaders()
		heads.add('Content-Type', 'text/plain')
		heads.add('Content-Length', len(msg))
		self.sendHttpResponse(req, '501 Not Implemented', heads, msg)

	def sendHttpResponse(self, req, code, heads, body):
		self.write(
'''HTTP/%s %s\r\n%s\r\n\r\n''' % (req.version, code, heads.format()))
		self.write(body)
		if req.version < '1.1' or req.headers.get('Connection') == ['close']:
			self.closeCleanly()

	# "Chunked" transfer encoding states
	@onDataChunk.when('self._http_state == self.ST_CHUNK_SZ')
	def onChunkSize(self, data):
		if ';' in data:
			# we don't support any chunk extensions
			data = data[:data.find(';')]
		size = int(data, 16)
		if size == 0:
			self._http_state = self.ST_CHUNK_TRAILER
		else:
			self._http_state = self.ST_CHUNK_DATA
			self.setTerminator(size)

	@onDataChunk.when('self._http_state == self.ST_CHUNK_DATA')
	def onChunkData(self, data):
		self._chunks.append(data)
		self._http_state = self.ST_CHUNK_SZ
		self.setTerminator('\r\n')
		self.eatData(2) # Get rid of trailing CRLF

	@onDataChunk.when('self._http_state == self.ST_CHUNK_TRAILER')
	def onChunkTrailerHead(self, data):
		if not data.strip():
			# We've reached the end.. phew!
			data = ''.join(self._chunks)
			self._req.headers.add('Content-Length', len(data))
			self._req.headers.remove('Transfer-Encoding')
			self._req.body = data
			self._chunks = []
			self.getHandlerMethod(self._req.cmd)(self._req)
			self._http_state = self.ST_RLINE
		else:
			# Adding a header via the trailer...
			self._req.headers.add(*tuple(data.split(':', 1)))
