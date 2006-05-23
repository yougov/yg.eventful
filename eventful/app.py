import socket
import event
import traceback

from eventful import eventbase
from eventful import protocol
from eventful import logmod, log

class Application:
	def __init__(self, logger=None):
		if logger is None:
			logger = logmod.Logger()
		self.logger = logger
		self.addLog = self.logger.addLog
		self._services = []

	def run(self):
		logmod.setCurrentApplication(self)
		log.info('Starting eventful application')
		for s in self._services:
			s.bindAndListen()
			event.event(eventbase.event_read_boundSocket,
			handle=s.sock, evtype=event.EV_READ | event.EV_PERSIST, arg=s).add()

		while True:
			try:
				event.dispatch()
			except SystemExit:
				log.warn("-- SystemExit raised.. exiting main loop --")
				break
			except KeyboardInterrupt:
				log.warn("-- KeyboardInterrupt raised.. exiting main loop --")
				break
			except Exception, e:
				log.error("-- Unhandled Exception in main loop --")
				log.error(traceback.format_exc())

		log.info('Ending eventful application')

	def addService(self, service):
		self._services.append(service)
		
class Service:
	LQUEUE_SIZ = 500
	def __init__(self, protocolHandler, port, iface=''):
		self.port = port
		self.iface = iface
		self.sock = None
		assert issubclass(protocolHandler, protocol.ProtocolHandler), \
		"Argument 1 to Service() must be a Protocol Handler"
		self.protocolHandler = protocolHandler

	def handleCannotBind(self, reason):
		log.critical("service at %s:%s cannot bind: %s" % (self.iface or '*', 
				self.port, reason))
		raise

	def bindAndListen(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		try:
			sock.bind((self.iface, self.port))
		except socket.error, e:
			self.handleCannotBind(str(e))

		sock.listen(self.LQUEUE_SIZ)
		self.sock = sock

	def _get_listening(self):
		return self.sock is not None

	listening = property(_get_listening)

	def acceptNewConnection(self, sock, addr):
		prot = self.protocolHandler(sock, addr)
		prot.service = self
		prot.onProtocolHandlerCreate()
