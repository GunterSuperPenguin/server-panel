import threading
from dataclasses import dataclass

from .config import DEFAULT_SETTINGS, NAME_RE, SERVERS_DIR, server_path
from .hub import Hub
from .process import Server
from .settings import save_settings


class ServerNotFound(ValueError):
    pass


@dataclass
class Instance:
    name: str
    hub: Hub
    server: Server


_instances: dict[str, Instance] = {}
_lock = threading.Lock()


def get_instance(name):
    if not NAME_RE.match(name or "") or not server_path(name).is_dir():
        raise ServerNotFound("Server not found")
    with _lock:
        if name not in _instances:
            hub = Hub()
            _instances[name] = Instance(name, hub, Server(name, hub))
        return _instances[name]


def list_servers():
    names = sorted(p.name for p in SERVERS_DIR.iterdir() if p.is_dir() and NAME_RE.match(p.name))
    return [{"name": n, "state": _instances[n].hub.state if n in _instances else "stopped"} for n in names]


def create_server(name):
    name = (name or "").strip()
    if not NAME_RE.match(name):
        raise ValueError("Name: latin letters, digits, _ and -, up to 40 characters")
    try:
        server_path(name).mkdir()
    except FileExistsError:
        raise ValueError("A server with this name already exists")
    save_settings(name, DEFAULT_SETTINGS)
    get_instance(name).hub.log(
        f"[panel] Created servers/{name}. On the first start steamcmd will download the server files (several GB).")
    return name


def stop_all():
    threads = [threading.Thread(target=inst.server.stop) for inst in list(_instances.values())]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
