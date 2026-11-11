import shutil
import subprocess

from .config import DEFAULT_SERVER_CFG, MAX_CFG_BYTES, server_path
from .errors import LocalizedError


def _game_dir(name):
    return server_path(name) / "garrysmod"


def cfg_path(name):
    return _game_dir(name) / "cfg" / "server.cfg"


def list_gamemodes(name):
    try:
        entries = (_game_dir(name) / "gamemodes").iterdir()
        return sorted((p.name for p in entries if p.is_dir() and not p.name.startswith(".")), key=str.lower)
    except OSError:
        return []


def list_maps(name):
    try:
        return sorted({p.stem for p in (_game_dir(name) / "maps").glob("*.bsp")}, key=str.lower)
    except OSError:
        return []


def read_server_cfg(name):
    try:
        return cfg_path(name).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return DEFAULT_SERVER_CFG


def write_server_cfg(name, content):
    if not isinstance(content, str):
        raise LocalizedError("err-bad-request")
    content = content.replace("\r\n", "\n")
    if content and not content.endswith("\n"):
        content += "\n"
    if len(content.encode("utf-8")) > MAX_CFG_BYTES:
        raise LocalizedError("err-cfg-too-large")
    path = cfg_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_server_cfg(name):
    if not cfg_path(name).exists():
        write_server_cfg(name, DEFAULT_SERVER_CFG)


def open_folder(name):
    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener is None:
        raise LocalizedError("err-open-folder")
    try:
        subprocess.Popen([opener, str(server_path(name))], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        raise LocalizedError("err-open-folder")
