import tests

from eventful import *

def echo(foo):
	print foo

call_later(6, echo, "6 secs once...")
call_every(3, echo, "3 secs forever...")

Application().run()
