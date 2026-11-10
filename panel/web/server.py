import json
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ..config import HOST, PORT
from ..errors import LocalizedError
from ..hub import Hub
from ..locales import get_l10n, resolve_locale
from .api import ROUTES
from .events import encode
from .request import EventStream, Request
from .static import read_static


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        locale = resolve_locale(query.get("lang", [""])[0], self.headers.get("Accept-Language", ""))
        l10n = get_l10n(locale)
        try:
            data = self._read_body() if method == "POST" else {}
            route = ROUTES.get((method, url.path))
            if route is None:
                if method == "GET":
                    return self._send_static(url.path)
                raise LocalizedError("err-not-found", status=404)
            result = route(Request(query, data, locale))
            if isinstance(result, EventStream):
                self._stream(result.hub, locale)
            else:
                self._send_json(result)
        except LocalizedError as e:
            self._send_json({"error": l10n.format_value(e.key, e.params)}, e.status)
        except ValueError:
            self._send_json({"error": l10n.format_value("err-bad-request")}, 400)

    def _read_body(self):
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            raise LocalizedError("err-forbidden", status=403)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            raise LocalizedError("err-invalid-json")
        if not isinstance(data, dict):
            raise LocalizedError("err-invalid-json")
        return data

    def _send_bytes(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def _send_static(self, url_path):
        found = read_static(url_path)
        if found is None:
            raise LocalizedError("err-not-found", status=404)
        self._send_bytes(*found)

    def _stream(self, hub: Hub, locale):
        l10n = get_l10n(locale)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = hub.subscribe()
        try:
            while True:
                try:
                    data = "data: " + encode(q.get(timeout=15), l10n) + "\n\n"
                except queue.Empty:
                    data = ": ping\n\n"
                self.wfile.write(data.encode())
                self.wfile.flush()
        except OSError:
            pass
        finally:
            hub.unsubscribe(q)


def create_http_server():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.daemon_threads = True
    return httpd
