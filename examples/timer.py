import tests

from yg.eventful import *

def echo(foo, otimer=None):
	if otimer:
		if otimer.pending:
			print "Other time has %s until firing" % otimer.countdown
			if otimer.countdown > 60:
				otimer.cancel()
				print "Cancelled otimer"
		else:
			print "Other timer has fired already"
	print foo

bleh = call_later(6, echo, "6 secs once...")
boo = call_later(666, echo, "loong time")
call_every(3, echo, "3 secs forever...", bleh)
call_every(5, echo, "check long one", boo)

Application().run()
