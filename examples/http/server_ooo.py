import tests
import yg.eventful
from yg.eventful import Application, Service, log, Logger, call_later
from yg.eventful.proto.http import HttpServerProtocol, HttpHeaders

PORT = 5190
SERVER = 'bogosity/2.1'

class HttpChunkedTestServer(HttpServerProtocol):
    def on_init(self):
        HttpServerProtocol.on_init(self)
        self.log = log.get_sublogger('http-server', verbosity=yg.eventful.LOGLVL_INFO)
        self.on_HTTP_GET = self.delay_get

    def getStandardHeaders(self):
        heads = HttpHeaders()
        heads.add('Server', SERVER)
        return heads

    def delay_get(self, req):
        call_later(3, self.real_delay_get, req)
        self.on_HTTP_GET = self.chunk_get

    def real_delay_get(self, req):
        heads = self.getStandardHeaders()
        c = 'delayed.. boo!'
        heads.add('Content-Length', len(c))
        self.send_http_response(req, '200 OK', heads, c)

    def chunk_get(self, req):
        heads = self.getStandardHeaders()
        self.on_HTTP_GET = self.real_delay_get
        d = self.start_chunked_response(req, '200 OK', heads)
        d.add_callback(self.give_chunks)

    def give_chunks(self, r):
        r("this...\n")
        r("that...\n")
        r("the other...\n")
        extra_heads = HttpHeaders()
        extra_heads.add('Boo', 'hiss')
        r(None, extra_heads)

application = Application(logger=Logger(verbosity=yg.eventful.LOGLVL_DEBUG))
application.add_service(Service(HttpChunkedTestServer, PORT))
application.run()
