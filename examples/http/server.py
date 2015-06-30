import os
import mimetypes
import time
import event

import tests
import yg.eventful
from yg.eventful import Application, Service, log, Logger, ActivityTimeoutMixin
from yg.eventful.proto.http import HttpServerProtocol, HttpHeaders

PORT = 5190
BASE = '/home/jamwt'
DEFAULT = 'index.html'
SERVER = 'eventful-sample-http/1.0'

errors = {
	404 : ('404 Not Found', 'The specified resource was not found'),
	403 : ('403 Permission Denied', 'Access is restricted to this resource'),
}

def checkDir(f):
	try:
		os.listdir(os.path.dirname(f))
	except OSError, e:
		if e.errno == 2:
			return 404
		else:
			return 403

def isFile(f):
	return os.path.isfile(f)

class HttpServer(HttpServerProtocol):
	_mixins = [ActivityTimeoutMixin(input=10, output=10)]
	def on_init(self):
		HttpServerProtocol.on_init(self)
		self.log = log.get_sublogger('http-server', verbosity=yg.eventful.LOGLVL_INFO)
		self.add_signal_handler('inactivemixin.timeout', self.onInactiveTimeout)

	def onInactiveTimeout(self, event):
		print "timeout!"
		self.disconnect()

	def sendError(self, req, code, heads):
		top, content = errors[code]
		heads.add('Content-Type', 'text/plain')
		heads.add('Content-Length', len(content))
		self.send_http_response(req, top, heads, content)

	def getStandardHeaders(self):
		heads = HttpHeaders()
		heads.add('Server', SERVER)
		return heads

	def on_HTTP_GET(self, req):
		heads = self.getStandardHeaders()
		self.log.info("%s -- GET %s" % (self.remote_addr[0], req.url))
		fn = os.path.join(BASE, req.url[1:])
		if not fn or fn[-1] == '/':
			fn += DEFAULT
		r = checkDir(fn)
		if r:
			self.sendError(req, r, heads)
			return
		if not isFile(fn):
			self.sendError(req, 404, heads)
			return

		try:
			fd = open(fn)
		except:
			self.sendError(req, 403, heads)
			return

		s = os.stat(fn).st_size

		typ = mimetypes.guess_type(fn)[0]
		if typ is None:
			typ = 'application/octet-stream'
		heads.add('Content-Type', typ)
		heads.add('Content-Length', s)
		self.send_http_response(req, '200 OK', heads, fd)

	def on_HTTP_POST(self, req):
		heads = self.getStandardHeaders()
		self.log.debug("== POSTED =========================\n%s\n\n" % req.body)
		self.log.debug(req.headers._headers)
		self.sendError(req, 403, heads)

application = Application(logger=Logger(verbosity=yg.eventful.LOGLVL_DEBUG))
application.add_service(Service(HttpServer, PORT))
application.run()
