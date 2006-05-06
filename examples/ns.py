import tests
from eventful import Application, Service
from eventful.proto.netstring import NetstringProtocol

class EchoServer(NetstringProtocol):
	def onNetstringIn(self, s):
		self.sendNetstring("You said " + s)
		self.closeCleanly()

application = Application()
application.addService(Service(EchoServer, 10101))
application.run()
