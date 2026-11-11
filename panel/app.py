from . import registry
from .config import HOST, PORT, SERVERS_DIR
from .web.server import create_http_server


def main():
    SERVERS_DIR.mkdir(parents=True, exist_ok=True)
    httpd = create_http_server()
    print(f"GMod panel: http://{HOST}:{PORT} (Ctrl+C to exit)")
    print(f"Servers directory: {SERVERS_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping servers...")
        registry.stop_all()
