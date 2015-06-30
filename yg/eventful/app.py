import socket
import event
import traceback
import os
import fcntl
import errno
import thread
from Queue import Queue, Empty

from . import eventbase
from . import protocol
from . import logmod, log
from . import timers
from .util import set_nonblocking, until_concludes
from .defer import Deferred

class Application:
	def __init__(self, logger=None):
		self._run = False
		if logger is None:
			logger = logmod.Logger()
		self.logger = logger
		self.add_log = self.logger.add_log
		self._services = []
		self._ext_call_q = Queue()

	def run(self):
		self._run = True
		logmod.set_current_application(self)
		log.info('Starting eventful application')
		for s in self._services:
			s.bind_and_listen()
			event.event(eventbase.event_read_bound_socket,
			handle=s.sock, evtype=event.EV_READ | event.EV_PERSIST, arg=s).add()

		self.setup_wake_pipe()

		def checkpoint():
			if not self._run:
				raise SystemExit

		timers.call_every(1.0, checkpoint)

		self.setup()
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

	def setup_wake_pipe(self):
		'''Establish a pipe that can be used to wake up the main
		loop.
		'''
		thread.start_new_thread(lambda: None, ())
		self._wake_i, self._wake_o = os.pipe()
		set_nonblocking(self._wake_i)
		set_nonblocking(self._wake_o)
		event.event(self.wake_routine, handle=self._wake_i,
		evtype=event.EV_READ | event.EV_PERSIST).add()

	def wake_routine(self, ev, sock, evtype, svc):
		# clear the notifications
		try:
			until_concludes(os.read, sock, 8192)
		except (IOError, OSError), err:
			if err.args[0] != errno.EAGAIN:
				raise

		# call any callbacks from out of the main thread
		while True:
			try:
				call = self._ext_call_q.get(block=False)
			except Empty:
				break
			else:
				call()

	def wake(self, callback):
		self._ext_call_q.put(callback)
		until_concludes(os.write, self._wake_o, ' ')

	def add_service(self, service):
		service.application = self
		self._services.append(service)

	def halt(self):
		self._run = False

	def setup(self):
		pass

	def defer_to_thread(self, d, f, *args, **kw):
		def wrap():
			try:
				res = f(*args, **kw)
			except Exception, e:
				def cb_error():
					d.errback(e)
				self.wake(cb_error)
			else:
				def cb_success():
					d.callback(res)
				self.wake(cb_success)

		thread.start_new_thread(wrap, ())

class Service:
	LQUEUE_SIZ = 500
	def __init__(self, protocol_handler, port, iface=''):
		self.port = port
		self.iface = iface
		self.sock = None
		assert issubclass(protocol_handler, protocol.ProtocolHandler), \
		"Argument 1 to Service() must be a Protocol Handler"
		self.protocol_handler = protocol_handler
		self.application = None

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
		prot.application = self.application
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
