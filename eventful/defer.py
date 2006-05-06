## thank you, twisted.

class Deferred:
	def __init__(self):
		self.callbacks = []
		self.errbacks = []

	def addCallback(self, f, *args, **kw):
		self.callbacks.append((f, args, kw))

	def addErrback(self, f, *args, **kw):
		self.errbacks.append((f, args, kw))

	def callback(self, res):
		try:
			p = res
			for c, a, k in self.callbacks:
				p = c(p, *a, **k)
				if isinstance(p, self.__class__):
					# XXX -- is extend the right thing here?
					p.callbacks.extend(self.callbacks)
					p.errbacks.extend(self.errbacks)
					return
		except Exception, e:
			self.errback(e)

	def errback(self, e):
		p = e
		for e, a, k in self.errbacks:
			p = e(p, *a, **k)
		#XXX -- unhandled exception in errback?
