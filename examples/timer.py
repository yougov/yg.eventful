import tests

from eventful import *

def echo(foo):
	print foo

callLater(6, echo, "6 secs once...")
callEvery(3, echo, "3 secs forever...")

Application().run()
