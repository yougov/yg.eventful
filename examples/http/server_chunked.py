import tests
import yg.eventful
from yg.eventful import Application, Service, log, Logger
from yg.eventful.proto.http import HttpServerProtocol, HttpHeaders

PORT = 5190
SERVER = 'bogosity/2.1'

class HttpChunkedTestServer(HttpServerProtocol):
    def on_init(self):
        HttpServerProtocol.on_init(self)
        self.log = log.get_sublogger('http-server', verbosity=yg.eventful.LOGLVL_INFO)

    def getStandardHeaders(self):
        heads = HttpHeaders()
        heads.add('Server', SERVER)
        return heads

    def on_HTTP_GET(self, req):
        heads = self.getStandardHeaders()
        r = self.start_chunked_response(req, '200 OK', heads)
        r("this...\n")
        r("that...\n")
        r("the other...\n")
        extra_heads = HttpHeaders()
        extra_heads.add('Boo', 'hiss')
        r(None, extra_heads)

application = Application(logger=Logger(verbosity=yg.eventful.LOGLVL_DEBUG))
application.add_service(Service(HttpChunkedTestServer, PORT))
application.run()
