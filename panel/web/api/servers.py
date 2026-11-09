from ... import registry
from ..request import Request


def list_servers(req: Request):
    return registry.list_servers()


def create_server(req: Request):
    return {"name": registry.create_server(req.data.get("name"))}


ROUTES = {
    ("GET", "/api/servers"): list_servers,
    ("POST", "/api/servers"): create_server,
}
