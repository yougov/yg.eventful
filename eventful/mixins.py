import copy
import event

from eventful import log

class Mixin:
	def get_signal_handlers(self):
		raise NotImplementedError

class ActivityTimeoutMixin(Mixin):
	def __init__(self, input=None, output=None):
		if input:
			self.input = int(input)
		else:
			self.input = None

		if output:
			self.output = int(output)
		else:
			self.output = None

	def get_signal_handlers(self):
		print "get evh with %s" % self
		new = copy.copy(self)
		hands = {
			'prot.new_connection' : new.on_new_connection,
			'prot.disconnected' : new.on_disconnect
			}
		if self.input:
			hands['core.bytes_received'] = new.on_input
			hands['prot.set_readable'] = new.on_set_readable
		if self.output:
			hands['prot.bytes_sent'] = new.on_output
			hands['prot.set_writable'] = new.on_set_writable
		return hands

	def timeout(self, event, handle, evtype, prot):
		prot.emit('inactivemixin.timeout')

	def on_new_connection(self, prot, evt):
		log.debug("new conn for %s, mixin %s" % (prot, self))
		self.itimer = None
		if self.input:
			self.itimer = event.event(self.timeout,prot)
		self.otimer = None

	def on_disconnect(self, prot, evt):
		if self.itimer:
			self.itimer.delete()

		self.itimer = None

	def on_input(self, prot, evt, num):
		print '>>> input'
		if self.itimer.pending():
			self.itimer.delete()
			self.itimer.add(self.input)

	def on_set_readable(self, prot, evt, val):
		print '>>readable'
		self.itimer.delete()
		if val:
			print 'add readable'
			self.itimer.add(self.input)
			print 'is pending', self.itimer.pending()
