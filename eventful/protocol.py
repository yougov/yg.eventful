import event

from eventful import eventbase
from eventful import pipeline

class ProtocolHandler:
	def __init__(self, sock, addr):
		self.sock = sock
		self.remote_addr = addr

		self._rev = event.read(self.sock, eventbase.event_read_handler, self)
		self._wev = event.write(self.sock, eventbase.event_write_handler, self)
		self._renable = False
		self._wenable = False

	def onProtocolHandlerCreate(self):
		pass

	def setReadable(self, val):
		if val != self._renable:
			self._renable = val
			if val:
				self._rev.add()
			elif self._rev.pending():
				self._rev.delete()

	def setWritable(self, val):
		if val != self._wenable:
			self._wenable = val
			if val:
				self._wev.add()
			elif self._wev.pending():
				self._wev.delete()

	def onWritable(self):
		pass

	def onConnectionLost(self, reason=None):
		pass

	def onRawData(self, data):
		pass

	def __del__(self):
		self._rev = None
		self._wev = None

	def disconnect(self):
		self.sock.close()
		self.setWritable(False)
		self.setReadable(False)
		self.onDisconnect()

	def onDisconnect(self):
		pass

class PipelinedProtocolHandler(ProtocolHandler):
	def __init__(self, *args, **kw):
		ProtocolHandler.__init__(self, *args, **kw)
		self._pipeline = self.createPipeline()
		self.setImplicitWrite(True)

	def createPipeline(self):
		return pipeline.Pipeline()

	def setImplicitWrite(self, val):
		self._impWrite = val

	def write(self, dataOrFile):
		self._pipeline.add(dataOrFile)
		if self._impWrite and not self._wenable:
			self.setWritable(True)

	def onWritable(self):
		if self._pipeline.empty:
			self.setWritable(False)
		else:
			try:
				data = self._pipeline.read(eventbase.BUFSIZ)
			except pipeline.PipelineCloseRequest:
				self.disconnect()
				return
			bsent = self.sock.send(data)
			if bsent != len(data):
				self._pipeline.backup(data[bsent:])
			if self._pipeline.empty:
				self.setWritable(False)
			else:
				self.setWritable(True)

	def closeCleanly(self):
		self._pipeline.closeRequest()

class AutoTerminatingProtocol(PipelinedProtocolHandler):
	def __init__(self, *args, **kw):
		PipelinedProtocolHandler.__init__(self, *args, **kw)
		self._atinbuf = []
		self._atterm = '\r\n'
		self._atmark = 0
		
	def setTerminator(self, term):
		self._atterm = term
		self._scanData()

	def onRawData(self, data):
		self._atinbuf.append(data)
		self._atmark += len(data)
		self._scanData()

	def _scanData(self):
		'''Look for the terminator.
		'''
		ind = None
		all = None
		if type(self._atterm) is int:
			if self._atmark > self._atterm:
				ind = self._atmark
		else:
			all = ''.join(self._atinbuf)
			res = all.find(self._atterm)
			if res != -1:
				ind = res + len(self._atterm)
		if ind:
			if not all:
				all = ''.join(self._atinbuf)
			use = all[:ind]
			self._atinbuf = [all[ind:]]
			self.onDataChunk(use)
			self._scanData()

	def onDataChunk(self, data):
		pass
