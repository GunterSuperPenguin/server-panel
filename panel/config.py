import os
import re
from pathlib import Path

HOST = os.environ.get("PANEL_HOST", "127.0.0.1")
PORT = int(os.environ.get("PANEL_PORT", "8080"))

STATIC_DIR = Path(__file__).resolve().parent / "static"
SERVERS_DIR = Path(os.environ.get("PANEL_SERVERS_DIR", "servers")).expanduser().resolve()

APP_ID = "4020"

MAX_CFG_BYTES = 256 * 1024
DEFAULT_SERVER_CFG = 'sv_loadingurl "https://guntersuperpenguin.github.io/loading-logo/"\n'

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
SAFE_VALUE_RE = re.compile(r"^[\w.\-]+$")

DEFAULT_SETTINGS = {
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
