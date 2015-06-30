import tests
from yg.eventful import Application, Service, MessageProtocol
from yg.eventful import Deferred

class DelayEchoProtocolHandler(MessageProtocol):
	def on_init(self):
		self.set_readable(True)
		self.add_signal_handler('prot.message', self.message_in)

	def message_in(self, ev, msg):
		import time
		def write_out(r):
			self.write("You said: " + msg)

		def err_out(e):
			print 'An error occured!'
			print e

		self.application.defer_to_thread(
		Deferred().add_callback(write_out).add_errback(err_out), time.sleep, 7)

application = Application()
application.add_service(Service(DelayEchoProtocolHandler, 10109))
application.run()
