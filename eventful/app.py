import socket
import event
import traceback

from eventful import eventbase
from eventful import protocol
from eventful import logmod, log

class Application:
	def __init__(self, logger=None):
		self._run = False
		if logger is None:
			logger = logmod.Logger()
		self.logger = logger
		self.add_log = self.logger.add_log
		self._services = []

	def run(self):
		self._run = True
		logmod.set_current_application(self)
		log.info('Starting eventful application')
		for s in self._services:
			s.bind_and_listen()
			event.event(eventbase.event_read_bound_socket,
			handle=s.sock, evtype=event.EV_READ | event.EV_PERSIST, arg=s).add()

		while self._run:
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

	def add_service(self, service):
		self._services.append(service)
		
	def halt(self):	
		self._run = False
		
class Service:
	LQUEUE_SIZ = 500
	def __init__(self, protocol_handler, port, iface=''):
		self.port = port
		self.iface = iface
		self.sock = None
		assert issubclass(protocol_handler, protocol.ProtocolHandler), \
		"Argument 1 to Service() must be a Protocol Handler"
		self.protocol_handler = protocol_handler

	def handle_cannot_bind(self, reason):
		log.critical("service at %s:%s cannot bind: %s" % (self.iface or '*', 
				self.port, reason))
		raise

	def bind_and_listen(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		try:
			sock.bind((self.iface, self.port))
		except socket.error, e:
			self.handle_cannot_bind(str(e))

		sock.listen(self.LQUEUE_SIZ)
		self.sock = sock

	def _get_listening(self):
		return self.sock is not None

	listening = property(_get_listening)

	def accept_new_connection(self, sock, addr):
		prot = self.protocol_handler(sock, addr)
		prot.service = self
		prot.on_init()
		
class Client:
	def __init__(self, protocol, *args, **kw):
		self.protocol = protocol
		self.args = args
		self.kw = kw
		
	def connect(self, addr, port):	
		remote_addr = (addr, port)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect(remote_addr)
		p = self.protocol(sock, remote_addr, *self.args, **self.kw)
		p.on_init()
		p.service = None
		return p