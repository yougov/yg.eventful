import tests
from yg.eventful import Application, Service, MessageProtocol

class EchoProtocolHandler(MessageProtocol):
	def on_init(self):
		self.set_readable(True)
		self.add_signal_handler('prot.message', self.message_in)

	def message_in(self, ev, msg):
		self.write("You said: " + msg)

application = Application()
application.add_service(Service(EchoProtocolHandler, 10101))
application.run()
