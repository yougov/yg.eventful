import os

import tests
from eventful import Application, Service
from eventful.proto.http import HttpProtocol, HttpHeaders

BASE = '/home/jamie'

class HttpServer(HttpProtocol):
	def on_HTTP_GET(self, url, heads, data):
		fn = os.path.join(BASE, url[1:])
		s = os.stat(fn).st_size
		heads = HttpHeaders()
		heads.add('Content-Type', 'text/plain')
		heads.add('Connection', 'close')
		self.sendHttpResponse('200 OK', heads, 
		open(fn))
		self.closeCleanly()

application = Application()
application.addService(Service(HttpServer, 10101))
application.run()
