import asyncio
import locale
import datetime
from http.server import BaseHTTPRequestHandler
from io import StringIO
from urllib.parse import parse_qs
import json
from routes import Mapper

locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')

STATUS_CODE = {
    200: '0K',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    300: 'Multiple Choice',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'unused',
    307: 'Temporary Redirect',
    308: 'Permanent Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Payload Too Large',
    414: 'URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: 'I\'m a teapot',
    421: 'Misdirected Request',
    426: 'Upgrade Required',
    428: 'Precondition Required',
    429: 'Too Many Requests',
    431: 'Request Header Fields Too Large',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    506: 'Variant Also Negotiates',
    507: 'Variant Also Negotiates',
    511: 'Network Authentication Required'
}


class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, reader):
        self.reader = reader
        self.header = {}
        self.data = {}

    @asyncio.coroutine
    def process(self):
        ''' This method will be pparse the request '''
        if self.header != {}:
            raise Exception('Request is aready processed')

        request_text = b''
        while True:
            request_text += yield from self.reader.read(2)
            self.reader.feed_eof()
            if self.reader.at_eof():
                break

        yield from self._process_lines(request_text)

    @asyncio.coroutine
    def _process_lines(self, request_text):
        '''Convert header data in dict, detect body and call _process_body'''
        is_header = True
        body = []
        for line in request_text.split(b'\n'):
            if is_header:
                line = line.strip().replace(b'\r', b'')
                if line:
                    yield from self.parse_line(line)
                else:
                    is_header = False
            else:
                body.append(line)

        yield from self._process_body(b'\n'.join(body).decode())

    @asyncio.coroutine
    def _process_json_body(self, body):
        '''Process json body'''
        data = json.loads(body)
        for key, value in data.items():
            self.data[key] = value

    @asyncio.coroutine
    def _process_urlencoded_body(self, body):
        '''Process urlencoded body'''
        data = parse_qs(body)

        for key, value in data.items():
            if '[]' not in key:
                data[key] = value[-1]

            self.data[key] = data[key]

    @asyncio.coroutine
    def _process_body(self, body):
        '''Detect Content-Type and process body'''
        self.header.setdefault(
            'Content-Type',
            'application/x-www-form-urlencoded'
        )
        content_type = self.header['Content-Type']
        if content_type == 'application/x-www-form-urlencoded':
            yield from self._process_urlencoded_body(body)
        elif 'application/json' in content_type:
            yield from self._process_json_body(body)

    @asyncio.coroutine
    def parse_line(self, line):
        header = self.header
        if header == {}:
            data = line.split(b' ')
            header['METHOD'], header['PATH'], header['PROTOCOL'] = data
            header['METHOD'] = header['METHOD'].decode()
            header['PATH'] = header['PATH'].decode()
            header['PROTOCOL'] = header['PROTOCOL'].decode()
        else:
            key, *value = line.split(b':')
            header[key.decode()] = (b':'.join(value)).strip().decode()


class HttpResponse(object):
    '''The HTTP Response'''
    def __init__(self, writer, content='',
                 status_code=200, status_code_message=None):
        self._writer = writer
        self._headers = {}
        self.status_code = status_code
        self.status_code_message = status_code_message
        self.set_content(content)

    def get_status_code(self):
        '''Return the current status code'''
        return self.status_code

    def get_status_message(self):
        ''' Get status message '''
        if self.status_code_message:
            return self.status_code_message
        return STATUS_CODE[self.status_code]

    def set_content(self, content):
        ''' Set the content of response '''
        self._content = content

    def get_content(self):
        ''' Return the content '''
        return self._content

    def get_header(self):
        ''' Get the repsonse header '''
        self.header_defaults()
        header = 'HTTP/1.1 {} {}'.format(
            self.get_status_code(),
            self.get_status_message()
        )
        for key, value in self._headers.items():
            header += '\n{}: {}'.format(key, value)
        return header

    def set_header(self, key, value):
        '''Set a header'''
        self._headers[key] = value

    def header_defaults(self):
        self._headers.setdefault('Server', 'Python Asyncio')
        self._headers.setdefault('Content-Type', 'text/plain')
        self._headers.setdefault(
            'Date',
            datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        )
        self._headers.setdefault(
            'Last-Modified',
            datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        )

    def get_response(self):
        '''Get the response'''
        return '{}\n\n{}'.format(self.get_header(), self.get_content()).encode()

    @asyncio.coroutine
    def close(self):
        self._writer.write(self.get_response())
        yield from self._writer.drain()
        self._writer.close()


class App(object):
    def __init__(self):
        self._loop_control = False
        self._mapper = Mapper()

    @asyncio.coroutine
    def reverse_url(self, request):
        path = request.header['PATH']
        return self._mapper.match(path)

    @asyncio.coroutine
    def handle(self, reader, writer):
        request = HTTPRequest(reader)
        yield from request.process()
        response = HttpResponse(writer)
        reverse = yield from self.reverse_url(request)
        fn = reverse.pop('_fn')
        yield from fn(request, response, **reverse)
        # addr = writer.get_extra_info('peername')
        # print("Received from {}".format(addr))

    def route(self, url, name=None, **kwargs):
        def decorator(fn):
            coro = asyncio.coroutine(fn)
            self._mapper.connect(name, url, _fn=coro, **kwargs)
        return decorator

    def start(self, loop=None, host='127.0.0.1', port=8888):
        if loop is None:
            loop = asyncio.get_event_loop()
            self._loop_control = True
        coro = asyncio.start_server(self.handle, host, port, loop=loop)
        server = loop.run_until_complete(coro)

        # Serve requests until Ctrl+C is pressed
        print('Serving on {}'.format(server.sockets[0].getsockname()))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        server.close()
        loop.run_until_complete(server.wait_closed())
        if self._loop_control:
            loop.close()

app = App()


@app.route('/')
def hello_world(request, response):
    response.set_content(str(request.header))
    yield from response.close()


app.start()
