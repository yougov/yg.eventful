import event
import socket

BUFSIZ = 65536

def event_read_bound_socket(ev, sock, evtype, svc):
	'''The read-event handler for the listening socket, which 
	accepts() and creates the request handler and other neccessary
	events.
	'''
	client_sock, address = sock.accept()
	svc.accept_new_connection(client_sock, address)
	
def event_write_handler(handler):
	'''The basic pyevent write-event handler which delegates 
	the response to the appropriate requesthandler.
	'''
	try:
		handler.on_writable()
	except socket.error:
		handler._close(client=True)
	if handler._wenable:
		return handler._wev

def event_read_handler(handler):
	'''The basic pyevent read-event handler which delegates
	the request/read data to the appropriate requesthandler.
	'''
	disconnect_reason = None
	try:
		data = handler.sock.recv(BUFSIZ)
	except socket.error, e:
		data = ''
		disconnect_reason = str(e)
		
	if not data:
		handler._close(client=True, reason=disconnect_reason)
	else:
		handler.emit('core.bytes_received', len(data))
		handler.on_raw_data(data)

	if handler._renable:
		return handler._rev
