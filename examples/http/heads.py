import tests
from yg.eventful.proto.http import *

heads = \
'''Content-Type: text/html\r
Content-Length: 3923\r
Accepts: one, two, three\r
	four, five, six\r
And: seven\r
Content-Type: text/plain'''

h = HttpHeaders()
h.parse(heads)
print(h._headers)
