import tests
from eventful.proto.http import *

heads = \
'''Content-Type: text/html\r
Content-Length: 3923\r
Accepts: one, two, three\r
	four, five, six\r
And: seven\r
Content-Type: text/plain'''

h = HttpHeaders(heads)
h.parse()
print h._headers
