import tests
from yg.eventful.proto.http import *

print parse_request_line('POST /blah?one=one HTTP/1.1')
print parse_request_line('GET /blah?one=one')
