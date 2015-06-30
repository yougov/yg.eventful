import event
from . import eventbase
from . import pipeline

def no_dbl_prot(f):
	def real_signal_call(prot, *args, **kw):
		return f(*args, **kw)
	return real_signal_call

class ProtocolHandler:
	_mixins = []
	def __init__(self, sock, addr):
		self.service = None
		self.application = None
		self.sock = sock
		self.remote_addr = addr

		self._rev = event.read(self.sock, eventbase.event_read_handler, self)
		self._wev = event.write(self.sock, eventbase.event_write_handler, self)
		self._renable = False
		self._wenable = False

		# Mix-Ins
		self._sighand = {}
		self._setup_mixins()
		self.closed = False

		self.emit('prot.new_connection')

	def _setup_mixins(self):
		for m in self._mixins:
			for ev, f in m.get_signal_handlers().iteritems():
				self._sighand.setdefault(ev, []).append(f)

	def add_mixin(self, m):
		for ev, f in m.get_signal_handlers().iteritems():
			self._sighand.setdefault(ev, []).append(f)

	def add_signal_handler(self, ev, f):
		self._sighand.setdefault(ev, []).append(no_dbl_prot(f))

	def set_signal_handler(self, ev, f):
		self._sighand[ev] = [f]

	def remove_signal_handler(self, ev, f):
		if ev in self._sighand and f in self._sighand[ev]:
			del self._sighand[ev][f]

	def remove_signal_handlers(self, ev):
		if ev in self._sighand:
			del self._sighand[ev]

	def will_handle(self, ev):
		return bool(self._sighand.get(ev))

	def emit(self, event, *args, **kw):
		try:
			fs = self._sighand[event]
		except KeyError:
			self._sighand[event] = []
			return
		r = None
		for f in fs:
			r = f(self, event, *args, **kw)
		return r

	def on_init(self):
		pass

	def set_readable(self, val):
		if val != self._renable:
			self._renable = val
			self.emit('prot.set_readable', val)
			if val:
				self._rev.add()
			elif self._rev.pending():
				self._rev.delete()

	def set_writable(self, val):
		if val != self._wenable:
			self._wenable = val
			self.emit('prot.set_writable', val)
			if val:
				self._wev.add()
			elif self._wev.pending():
				self._wev.delete()

	def on_writable(self):
		pass

	def on_raw_data(self, data):
		pass

	def disconnect(self):
		self.sock.close()
		self._close()

	def _close(self, client=False, reason=None):
		self.set_writable(False)
		self.set_readable(False)
		self._rev = None
		self._wev = None
		self.closed = True
		self.emit('prot.disconnected')
		if client:
			self.emit('prot.remote_dropped', reason)
		self._sighand = None
		self.service = None
		self.application = None

class PipelinedProtocolHandler(ProtocolHandler):
	def __init__(self, *args, **kw):
		ProtocolHandler.__init__(self, *args, **kw)
		self._pipeline = self.create_pipeline()
		self.set_implicit_write(True)

	def create_pipeline(self):
		return pipeline.Pipeline()

	def set_implicit_write(self, val):
		self._imp_write = val

	def write(self, data_or_file):
		self._pipeline.add(data_or_file)
		if self._imp_write and not self._wenable:
			self.set_writable(True)

	def on_writable(self):
		if self._pipeline.empty:
			self.set_writable(False)
		else:
			try:
				data = self._pipeline.read(eventbase.BUFSIZ)
			except pipeline.PipelineCloseRequest:
				self.disconnect()
				return
			bsent = self.sock.send(data)
			self.emit('prot.bytes_sent', bsent)
			if bsent != len(data):
				self._pipeline.backup(data[bsent:])
			if self._pipeline.empty:
				self.set_writable(False)
			else:
				self.set_writable(True)

	def close_cleanly(self):
		self._pipeline.close_request()

class MessageProtocol(PipelinedProtocolHandler):
	def __init__(self, *args, **kw):
		PipelinedProtocolHandler.__init__(self, *args, **kw)
		self._atinbuf = []
		self._atterm = '\r\n'
		self._atmark = 0
		self._eat = 0
		self._mess_sig = 'prot.message'
		self._mess_iter = None
		self.add_signal_handler("prot.set_readable", self._set_readable)

	def request_message(self, signal='prot.message', bytes=0, sentinel='\r\n', _keepiter=False):
		self._atterm = bytes or sentinel
		self._mess_sig = signal
		if not _keepiter and self._mess_iter:
			self._mess_iter = None

	def set_message_iter(self, iter):
		self._mess_iter = iter
		kw = self._mess_iter.next()
		kw['_keepiter'] = True
		self.request_message(**kw)

	def on_raw_data(self, data):
		self._atinbuf.append(data)
		self._atmark += len(data)
		self._scan_data()

	def _set_readable(self, evt, readable):
		if readable and self._atinbuf:
			self._scan_data()

	def _scan_data(self):
		'''Look for the message
		'''
		while 1:
			ind = None
			all = None
			if type(self._atterm) is int:
				if self._atmark >= self._atterm:
					ind = self._atterm
			else:
				all = ''.join(self._atinbuf)
				res = all.find(self._atterm)
				if res != -1:
					ind = res + len(self._atterm)
			if ind is None:
				break
			if all is None:
				all = ''.join(self._atinbuf)
			use = all[:ind]
			self.emit(self._mess_sig, use)
			if self._mess_iter:
				kw = self._mess_iter.next()
				kw['_keepiter'] = True
				self.request_message(**kw)

			self._atinbuf = [all[ind + self._eat:]]
			self._atmark = len(self._atinbuf[0])
			self._eat = 0
			if self.closed or not self._renable:
				return
		if self._atterm is not None:
			self.set_readable(True)

	def skip_input(self, l):
		self._eat += l

	def pop_buffer(self):
		all = ''.join(self._atinbuf)
		self._atinbuf = []
		self._atmark = 0
		return all
