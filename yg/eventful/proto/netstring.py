from ..protocol import MessageProtocol
from ..util import encode_netstring

class NetstringProtocol(MessageProtocol):
	def on_init(self):
		MessageProtocol.on_init(self)

		# Message part handlers
		self.add_signal_handler('netstring.message.size', self._on_size_chunk)
		self.add_signal_handler('netstring.message.data', self._on_data_chunk)

		# Alternate between parts
		self.set_message_iter(self.normal_flow())

	def normal_flow(self):
		size_msg = dict(signal='netstring.message.size', sentinel=':')
		while 1:
			# Each iter is one message
			yield size_msg
			yield dict(signal='netstring.message.data', bytes=self.siz)

	def _on_size_chunk(self, ev, data):
		try:
			self.siz = int(data[:-1])
		except ValueError:
			self.close_cleanly()

	def _on_data_chunk(self, ev, data):
		self.emit('netstring.in', data)

	def send_netstring(self, s):
		self.write(encode_netstring(s))
