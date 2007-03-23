LOG_TO_SCREEN=False
PORT=7080
# Cherrypy 2.2.1
from server_wsgi import WSGIApplication
from cherrypy._cpwsgi import wsgiApp as cpwsgi_app
import cherrypy

big_s = "Hello, World!" * 50000
class Test:
	@cherrypy.expose
	def index(self):
		return "Hello, World!"

	@cherrypy.expose
	def big(self):
		return big_s
cherrypy.root = Test()

if __name__ == '__main__':
	import sys
	cherrypy.config.update({
		'server.environment' : 'production',
		'server.log_to_screen' : LOG_TO_SCREEN,
		})
	if len(sys.argv) > 1 and sys.argv[1] == 'normal':
		print 'Using regular cherrypy WSGI server'
		cherrypy.config.update({
			'server.socket_port' : PORT,
			})
		cherrypy.server.start()
	else:
		print "Using eventful's WSGI wrapping example"
		cherrypy.config.update({
			'server.protocol_version' : 'HTTP/1.1',
			})
		cherrypy.server.start(init_only=True, server_class=None)
		WSGIApplication(cpwsgi_app, PORT).run()
