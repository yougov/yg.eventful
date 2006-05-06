import event
import socket

BUFSIZ = 65536

def event_read_boundSocket(ev, sock, evtype, svc):
	'''The read-event handler for the listening socket, which 
	accepts() and creates the request handler and other neccessary
	events.
	'''
	client_sock, address = sock.accept()
	svc.acceptNewConnection(client_sock, address)
	
def event_write_handler(handler):
	'''The basic pyevent write-event handler which delegates 
	the response to the appropriate requesthandler.
	'''
	try:
		handler.onWritable()
	except socket.error:
		handler.onConnectionLost()
	if handler._wenable:
		return handler._wev

def event_read_handler(handler):
	'''The basic pyevent read-event handler which delegates
	the request/read data to the appropriate requesthandler.
	'''
	disconnectReason = None
	try:
		data = handler.sock.recv(BUFSIZ)
	except socket.error, e:
		data = ''
		disconnectReason = str(e)
		
	if not data:
		handler.onConnectionLost(disconnectReason)
	else:
		handler.onRawData(data)

	if handler._renable:
		return handler._rev
