import os
import pty
import re
import signal
import subprocess
import threading

from .config import APP_ID, server_path
from .errors import LocalizedError
from .files import ensure_server_cfg
from .hub import Hub
from .settings import load_settings

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|[\x00-\x08\x0b-\x1f\x7f]")
P2P = re.compile(r"connect (p2p:\d+)")


class Server:
    def __init__(self, name: str, hub: Hub):
        self.name = name
        self.hub = hub
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.proc: subprocess.Popen | None = None
        self.master: int | None = None
        self.phase: str | None = None
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
            raise LocalizedError("err-server-not-running")
        os.write(self.master, (text + "\n").encode())
        self.hub.log(text, "cmd")

    def _loop(self):
        hub = self.hub
        hub.set("starting")
        try:
            while not self.stopping:
                cfg = load_settings(self.name)
                server_dir = server_path(self.name)
                if cfg["update_on_start"]:
                    self._steamcmd(server_dir)
                    if self.stopping:
                        break
                if not (server_dir / "srcds_run").exists():
                    hub.log_key("log-no-srcds", name=self.name)
                    break
                ensure_server_cfg(self.name)
                hub.set("starting")
                code = self._run_server(cfg, server_dir)
                hub.log_key("log-exited", code=str(code))
                if self.stopping or code == 0 or not cfg["auto_restart"]:
                    break
                hub.log_key("log-restarting")
                hub.set("starting")
                self.wake.wait(3)
        finally:
            self.phase = None
            hub.set("stopped")

    def _steamcmd(self, server_dir):
        self.hub.log_key("log-steamcmd-start")
        cmd = ["steamcmd", "+force_install_dir", str(server_dir), "+login", "anonymous",
               "+app_update", APP_ID, "-beta", "public", "validate", "+quit"]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="replace", start_new_session=True)
        except FileNotFoundError:
            self.hub.log_key("log-steamcmd-missing")
            return
        self.proc, self.phase = proc, "steamcmd"
        for line in proc.stdout or []:
            line = ANSI.sub("", line).strip()
            if line:
                self.hub.log(line)
        proc.wait()
        self.proc = None

    def _run_server(self, cfg, server_dir):
        cmd = ["./srcds_run", "-game", "garrysmod", "-norestart", "-port", str(cfg["port"]),
               "+maxplayers", str(cfg["maxplayers"]), "+map", cfg["map"],
               "+developer", "1", "+gamemode", cfg["gamemode"],
               "+sv_hibernate_think", "1", "+sv_lan", "0", "-p2p"]
        if cfg["workshop_collection"]:
            cmd += ["+host_workshop_collection", cfg["workshop_collection"]]
        self.hub.log_key("log-starting", cmd=" ".join(cmd))

        master, slave = pty.openpty()
        proc = subprocess.Popen(cmd, cwd=server_dir, stdin=slave, stdout=slave, stderr=slave,
                                start_new_session=True)
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
        for sig, timeout in ((signal.SIGINT, 8), (signal.SIGTERM, 5), (signal.SIGKILL, 5)):
            try:
                os.killpg(proc.pid, sig)
                proc.wait(timeout)
                return
            except ProcessLookupError:
                return
            except subprocess.TimeoutExpired:
                continue
