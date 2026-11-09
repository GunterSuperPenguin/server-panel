import json
import os
import pty
import queue
import re
import signal
import subprocess
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("PANEL_HOST", "127.0.0.1")
PORT = int(os.environ.get("PANEL_PORT", "8080"))
BASE = Path(__file__).resolve().parent
SERVERS_DIR = BASE / "servers"
SERVERS_DIR.mkdir(exist_ok=True)

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
ANSI = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|[\x00-\x08\x0b-\x1f\x7f]"
)
P2P = re.compile(r"connect (p2p:\d+)")
SAFE = re.compile(r"^[\w.\-]+$")

DEFAULTS = {
    "map": "gm_construct",
    "gamemode": "sandbox",
    "workshop_collection": "",
    "maxplayers": 12,
    "port": 27015,
    "update_on_start": True,
    "auto_restart": True,
}


def server_path(name):
    return SERVERS_DIR / name


def load_config(name):
    cfg = dict(DEFAULTS)
    try:
        cfg.update(
            json.loads((server_path(name) / "panel.json").read_text(encoding="utf-8"))
        )
    except (OSError, ValueError):
        pass
    return cfg


def save_config(name, cfg):
    (server_path(name) / "panel.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def validate_config(name, data):
    cfg = load_config(name)
    for key, title in (("map", "Map"), ("gamemode", "Gamemode")):
        value = str(data.get(key, cfg[key])).strip()
        if not SAFE.match(value):
            raise ValueError(f"{title}: only letters, digits, _ . - are allowed")
        cfg[key] = value
    wc = str(data.get("workshop_collection", "")).strip()
    if wc and not wc.isdigit():
        raise ValueError("Workshop collection ID must contain digits only")
    cfg["workshop_collection"] = wc
    for key, title, lo, hi in (
        ("maxplayers", "Max players", 1, 128),
        ("port", "Port", 1024, 65535),
    ):
        try:
            value = int(data.get(key, cfg[key]))
        except (TypeError, ValueError):
            raise ValueError(f"{title} must be a number")
        if not lo <= value <= hi:
            raise ValueError(f"{title} must be between {lo} and {hi}")
        cfg[key] = value
    cfg["update_on_start"] = bool(data.get("update_on_start"))
    cfg["auto_restart"] = bool(data.get("auto_restart"))
    return cfg


class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients = []
        self.history = deque(maxlen=3000)
        self.state = "stopped"
        self.p2p = None

    def _state_msg(self):
        return {"type": "state", "state": self.state, "p2p": self.p2p}

    def _push(self, msg):
        for q in self.clients:
            q.put(msg)

    def log(self, text):
        with self.lock:
            self.history.append(text)
            self._push({"type": "line", "text": text})

    def set(self, state, p2p=None):
        with self.lock:
            self.state, self.p2p = state, p2p
            self._push(self._state_msg())

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            q.put(self._state_msg())
            q.put({"type": "history", "lines": list(self.history)})
            self.clients.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)


class Server:
    def __init__(self, name, hub):
        self.name = name
        self.hub = hub
        self.lock = threading.Lock()
        self.thread = None
        self.proc = None
        self.master = None
        self.phase = None
        self.stopping = False
        self.wake = threading.Event()

    def active(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self):
        with self.lock:
            if self.active():
                return False
            self.stopping = False
            self.wake.clear()
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return True

    def stop(self):
        if not self.active():
            return
        self.stopping = True
        self.wake.set()
        self.hub.set("stopping")
        self._terminate()
        t = self.thread
        if t:
            t.join(timeout=60)

    def restart(self):
        def job():
            self.stop()
            self.start()

        threading.Thread(target=job, daemon=True).start()

    def command(self, text):
        if self.phase != "server" or self.master is None:
            raise RuntimeError("Server is not running")
        os.write(self.master, (text + "\n").encode())
        self.hub.log("> " + text)

    def _loop(self):
        hub = self.hub
        hub.set("starting")
        try:
            while not self.stopping:
                cfg = load_config(self.name)
                server_dir = server_path(self.name)
                if cfg["update_on_start"]:
                    self._steamcmd(server_dir)
                    if self.stopping:
                        break
                if not (server_dir / "srcds_run").exists():
                    hub.log(
                        f"[panel] servers/{self.name} has no srcds_run - enable steamcmd updates in the settings"
                    )
                    break
                hub.set("starting")
                code = self._run_server(cfg, server_dir)
                hub.log(f"[panel] Server exited with code {code}")
                if self.stopping or code == 0 or not cfg["auto_restart"]:
                    break
                hub.log("[panel] Restarting in 3 seconds...")
                hub.set("starting")
                self.wake.wait(3)
        finally:
            self.phase = None
            hub.set("stopped")

    def _steamcmd(self, server_dir):
        self.hub.log("[panel] Installing/updating the server with steamcmd...")
        cmd = [
            "steamcmd",
            "+force_install_dir",
            str(server_dir),
            "+login",
            "anonymous",
            "+app_update",
            "4020",
            "-beta",
            "public",
            "validate",
            "+quit",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                start_new_session=True,
            )
        except FileNotFoundError:
            self.hub.log("[panel] steamcmd not found in PATH - update skipped")
            return
        self.proc, self.phase = proc, "steamcmd"
        for line in proc.stdout or []:
            line = ANSI.sub("", line).strip()
            if line:
                self.hub.log(line)
        proc.wait()
        self.proc = None

    def _run_server(self, cfg, server_dir):
        cmd = [
            "./srcds_run",
            "-game",
            "garrysmod",
            "-norestart",
            "-port",
            str(cfg["port"]),
            "+maxplayers",
            str(cfg["maxplayers"]),
            "+map",
            cfg["map"],
            "+developer",
            "1",
            "+gamemode",
            cfg["gamemode"],
            "+sv_hibernate_think",
            "1",
            "+sv_lan",
            "0",
            "-p2p",
        ]
        if cfg["workshop_collection"]:
            cmd += ["+host_workshop_collection", cfg["workshop_collection"]]
        self.hub.log("[panel] Starting: " + " ".join(cmd))

        master, slave = pty.openpty()
        proc = subprocess.Popen(
            cmd,
            cwd=server_dir,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
        )
        os.close(slave)
        self.proc, self.master, self.phase = proc, master, "server"
        if self.stopping:
            self._terminate()

        buf = b""
        while True:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            *lines, buf = re.split(rb"[\r\n]+", buf)
            for raw in lines:
                self._line(raw)
        if buf:
            self._line(buf)
        code = proc.wait()
        os.close(master)
        self.proc, self.master = None, None
        return code

    def _line(self, raw):
        text = ANSI.sub("", raw.decode("utf-8", "replace")).rstrip()
        if not text:
            return
        self.hub.log(text)
        m = P2P.search(text)
        if m:
            self.hub.set("running", m.group(1))

    def _terminate(self):
        proc = self.proc
        if not proc or proc.poll() is not None:
            return
        if self.phase == "server" and self.master is not None:
            try:
                os.write(self.master, b"quit\n")
                proc.wait(15)
                return
            except (OSError, subprocess.TimeoutExpired):
                pass
        for sig, timeout in (
            (signal.SIGINT, 8),
            (signal.SIGTERM, 5),
            (signal.SIGKILL, 5),
        ):
            try:
                os.killpg(proc.pid, sig)
                proc.wait(timeout)
                return
            except ProcessLookupError:
                return
            except subprocess.TimeoutExpired:
                continue


instances = {}
registry_lock = threading.Lock()


def get_instance(name):
    if not NAME_RE.match(name or "") or not server_path(name).is_dir():
        raise ValueError("Server not found")
    with registry_lock:
        if name not in instances:
            hub = Hub()
            instances[name] = (hub, Server(name, hub))
        return instances[name]


def list_servers():
    names = sorted(
        p.name for p in SERVERS_DIR.iterdir() if p.is_dir() and NAME_RE.match(p.name)
    )
    return [
        {"name": n, "state": instances[n][0].state if n in instances else "stopped"}
        for n in names
    ]


def create_server(name):
    name = (name or "").strip()
    if not NAME_RE.match(name):
        raise ValueError("Name: latin letters, digits, _ and -, up to 40 characters")
    try:
        server_path(name).mkdir()
    except FileExistsError:
        raise ValueError("A server with this name already exists")
    save_config(name, DEFAULTS)
    get_instance(name)[0].log(
        f"[panel] Created servers/{name}. On the first start steamcmd will download the server files (several GB)."
    )
    return name


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _server_name(self):
        return parse_qs(urlparse(self.path).query).get("server", [""])[0]

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/":
                body = (BASE / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/servers":
                self._json(list_servers())
            elif path == "/api/config":
                name = self._server_name()
                get_instance(name)
                self._json(load_config(name))
            elif path == "/api/events":
                self._events(get_instance(self._server_name())[0])
            else:
                self._json({"error": "Not found"}, 404)
        except ValueError as e:
            self._json({"error": str(e)}, 404)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self._json({"error": "Forbidden"}, 403)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json({"error": "Invalid JSON"}, 400)

        path = urlparse(self.path).path
        try:
            if path == "/api/servers":
                return self._json({"name": create_server(data.get("name"))})
            name = self._server_name()
            server = get_instance(name)[1]
            if path == "/api/start":
                self._json({"ok": server.start()})
            elif path == "/api/stop":
                threading.Thread(target=server.stop, daemon=True).start()
                self._json({"ok": True})
            elif path == "/api/restart":
                server.restart()
                self._json({"ok": True})
            elif path == "/api/command":
                cmd = str(data.get("command", "")).strip()
                if cmd:
                    server.command(cmd)
                self._json({"ok": True})
            elif path == "/api/config":
                cfg = validate_config(name, data)
                save_config(name, cfg)
                self._json(cfg)
            else:
                self._json({"error": "Not found"}, 404)
        except (ValueError, RuntimeError) as e:
            self._json({"error": str(e)}, 400)

    def _events(self, hub):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = hub.subscribe()
        try:
            while True:
                try:
                    data = (
                        "data: "
                        + json.dumps(q.get(timeout=15), ensure_ascii=False)
                        + "\n\n"
                    )
                except queue.Empty:
                    data = ": ping\n\n"
                self.wfile.write(data.encode())
                self.wfile.flush()
        except OSError:
            pass
        finally:
            hub.unsubscribe(q)


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.daemon_threads = True
    print(f"GMod panel: http://{HOST}:{PORT} (Ctrl+C to exit)")
    print(f"Servers directory: {SERVERS_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping servers...")
        threads = [threading.Thread(target=srv.stop) for _, srv in instances.values()]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


if __name__ == "__main__":
    main()
