import event

def call_later(t, f, *args):
	event.timeout(t, f, *args).add()

def call_every(t, f, *args):
	event.timeout(t, _call_again, t, f, *args).add()

def _call_again(t, f, *args):
	f(*args)
	event.timeout(t, _call_again, t, f, *args).add()
