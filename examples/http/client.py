"""Fire off a few HTTP requests.
"""
import socket

import tests
from yg.eventful.proto.http import HttpClient, HttpHeaders
from yg.eventful import Application

resp_count = 0
def print_response(res, num):
	'''print a result, and shutdown after
	all are done.
	'''
	global resp_count
	resp, body = res
	print '=' * 72 + '\nReceived Response #%d' % num
	print resp.request.url
	print resp
	print 'body length:', len(body)
	resp_count +=1
	print '\n' * 3
	if resp_count == 3:
		print 'got all requests; shutting down...'
		app.halt()

app = Application()
c = HttpClient()


# let's look up the names now b/c we don't have an async
# resolver handy -- a few requests to jamwt.com
heads = HttpHeaders()
heads.add("host", "www.jamwt.com")
heads.add("user-agent", "eventful-http-example-client/1.0")
connection = c.connect(socket.gethostbyaddr("www.jamwt.com")[-1][0], 80)
connection.request("GET", "/", heads, '').add_callback(print_response, 1)
connection.request("GET", "/Py-TOC/", heads, '').add_callback(print_response, 2)

# now one to google.. which will probably
# finish first!
heads = HttpHeaders()
heads.add("host", "www.google.com")
heads.add("user-agent", "eventful-http-example-client/1.0")
connection = c.connect(socket.gethostbyaddr("www.google.com")[-1][0], 80)
connection.request("GET", "/", heads, '').add_callback(print_response, 3)

# start the event loop
# will go until halt() is called
app.run()
