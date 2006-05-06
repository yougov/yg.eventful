import tests
from eventful import Application, Service, AutoTerminatingProtocol

class EchoProtocolHandler(AutoTerminatingProtocol):
	def onProtocolHandlerCreate(self):
		self.setReadable(True)

	def onDataChunk(self, data):
		self.write(data)
		self.closeCleanly()

application = Application()
application.addService(Service(EchoProtocolHandler, 10101))
application.run()
