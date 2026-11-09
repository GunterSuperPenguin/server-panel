import json
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ..config import HOST, PORT
from ..hub import Hub
from ..registry import ServerNotFound
from .api import ROUTES
from .request import EventStream, HttpError, Request
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
        try:
            data = self._read_body() if method == "POST" else {}
            route = ROUTES.get((method, url.path))
            if route is None:
                if method == "GET":
                    return self._send_static(url.path)
                raise HttpError(404, "Not found")
            result = route(Request(parse_qs(url.query), data))
            if isinstance(result, EventStream):
                self._stream(result.hub)
            else:
                self._send_json(result)
        except HttpError as e:
            self._send_json({"error": e.message}, e.status)
        except ServerNotFound as e:
            self._send_json({"error": str(e)}, 404)
        except (ValueError, RuntimeError) as e:
            self._send_json({"error": str(e)}, 400)

    def _read_body(self):
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            raise HttpError(403, "Forbidden")
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            raise HttpError(400, "Invalid JSON")
        if not isinstance(data, dict):
            raise HttpError(400, "Invalid JSON")
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
            raise HttpError(404, "Not found")
        self._send_bytes(*found)

    def _stream(self, hub: Hub):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = hub.subscribe()
        try:
            while True:
                try:
                    data = "data: " + json.dumps(q.get(timeout=15), ensure_ascii=False) + "\n\n"
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
