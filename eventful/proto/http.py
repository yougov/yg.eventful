import dispatch

from eventful import AutoTerminatingProtocol

def parseRequestLine(line):
	items = line.split(' ')
	items[0] = items[0].upper()
	if len(items) == 2:
		return tuple(items) + ('0.9',)
	items[2] = items[2].split('/')[-1]
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
		self._headers.setdefault(k.lower(), []).append(v.strip())

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

class HttpProtocol(AutoTerminatingProtocol):
	ST_RLINE = 1
	ST_HEADS = 2
	ST_BODY_CLEN  = 3
	ST_BODY_CHUNK  = 4

	def onProtocolHandlerCreate(self):
		self.setReadable(True)
		self.setTerminator('\r\n')
		self._http_state = self.ST_RLINE
		self._req_cmd = None
		self._req_url = None
		self._req_version = None
		self._req_heads = None

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
		self._req_cmd = cmd
		self._req_url = url
		self._req_version = version
		self._http_state = self.ST_HEADS
		self.setTerminator('\r\n\r\n')

	@onDataChunk.when('self._http_state == self.ST_HEADS')
	def onHeaders(self, data):
		heads = HttpHeaders()
		heads.parse(data)
		nextState = self.checkForHttpBody(heads)
		if not nextState:
			self.getHandlerMethod(self._req_cmd)(self._req_url, heads, None)
		else:
			self._http_state = nextState

	@onDataChunk.when('self._http_state == self.ST_BODY_CLEN')
	def onEndBody(self, data):
		self.getHandlerMethod(self._req_cmd)(self._req_url, heads, data)
		self.setTerminator('\r\n')
		self._http_state = self.ST_RLINE

	def checkForHttpBody(self, heads):
		if 'Content-Length' in heads:
			self.setTerminator(int(heads['Content-Length']))
			return self.ST_BODY_CLEN
		return None

	def on_noHttpHandler(self, url, headers):
		self.write('no such handler for HTTP command %s' % self._req_cmd)
		self.closeCleanly()

	def sendHttpResponse(self, code, heads, body):
		self.write(
'''HTTP/%s %s\r\n%s\r\n\r\n''' % (self._req_version, code, heads.format()))
		self.write(body)
