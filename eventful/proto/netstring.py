import dispatch

from eventful.protocol import AutoTerminatingProtocol
from eventful.util import encodeNetstring

class NetstringProtocol(AutoTerminatingProtocol):
	MODE_SZ  = 1
	MODE_STR = 2
	def onProtocolHandlerCreate(self):
		AutoTerminatingProtocol.onProtocolHandlerCreate(self)
		self.setTerminator(':')
		self.netprot_mode = self.MODE_SZ

	@dispatch.generic()
	def onDataChunk(self, data):
		pass

	@onDataChunk.when('self.netprot_mode == MODE_SZ')
	def onSizeChunk(self, data):
		try:
			siz = int(data[:-1])
		except ValueError:
			self.closeCleanly()
			return
		self.netprot_mode = self.MODE_STR
		self.setTerminator(siz)

	@onDataChunk.when('self.netprot_mode == MODE_STR')
	def onSizeChunk(self, data):
		self.onNetstringIn(data)
		self.netprot_mode = self.MODE_SZ
		self.setTerminator(':')

	def sendNetstring(self, s):
		self.write(encodeNetstring(s))

	def onNetstringIn(self, data):
		pass
