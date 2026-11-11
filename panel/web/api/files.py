from ... import files
from ..request import Request


def get_options(req: Request):
    name = req.instance().name
    return {"gamemodes": files.list_gamemodes(name), "maps": files.list_maps(name)}


def get_server_cfg(req: Request):
    return {"content": files.read_server_cfg(req.instance().name)}


def put_server_cfg(req: Request):
    files.write_server_cfg(req.instance().name, req.data.get("content"))
    return {"ok": True}


def open_folder(req: Request):
    files.open_folder(req.instance().name)
    return {"ok": True}


ROUTES = {
    ("GET", "/api/options"): get_options,
    ("GET", "/api/server-cfg"): get_server_cfg,
    ("POST", "/api/server-cfg"): put_server_cfg,
    ("POST", "/api/open-folder"): open_folder,
}
