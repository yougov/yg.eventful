LOG_TO_SCREEN=False
PORT=7080
# Cherrypy 3
from server_wsgi import WSGIApplication
from cherrypy import Application
import cherrypy

big_s = "Hello, World!" * 50000
class Test:
	@cherrypy.expose
	def index(self):
		return "Hello, World!"

	@cherrypy.expose
	def big(self):
		return big_s
cherrypy.tree.mount(Test())

if __name__ == '__main__':
	import sys, os
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
		app = Application(Test())
		app.merge({
			'/static' : {
				'tools.staticdir.on' : True,
				'tools.staticdir.dir' : os.path.abspath('./static'),
			}
				
		})
		WSGIApplication(app, PORT).run()
