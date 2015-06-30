import tests
from yg.eventful import Application, Service
from yg.eventful.proto.netstring import NetstringProtocol

CLOSE = False

class EchoServer(NetstringProtocol):
	def on_init(self):
		NetstringProtocol.on_init(self)
		self.set_readable(True)
		self.add_signal_handler('netstring.in', self.on_netstring)

	def on_netstring(self, ev, s):
		self.send_netstring("You said " + s)
		if CLOSE:
			self.close_cleanly()

application = Application()
application.add_service(Service(EchoServer, 10101))
application.run()
