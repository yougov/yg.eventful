import event

def callLater(t, f, *args):
	event.timeout(t, f, *args).add()

def callEvery(t, f, *args):
	event.timeout(t, _callAgain, t, f, *args).add()

def _callAgain(t, f, *args):
	f(*args)
	event.timeout(t, _callAgain, t, f, *args).add()
