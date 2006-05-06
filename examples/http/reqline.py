import tests
from eventful.proto.http import *

print parseRequestLine('POST /blah?one=one HTTP/1.1')
print parseRequestLine('GET /blah?one=one')
