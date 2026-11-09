from ...settings import load_settings, save_settings, validate_settings
from ..request import Request


def get_settings(req: Request):
    return load_settings(req.instance().name)


def update_settings(req: Request):
    name = req.instance().name
    cfg = validate_settings(name, req.data)
    save_settings(name, cfg)
    return cfg


ROUTES = {
    ("GET", "/api/config"): get_settings,
    ("POST", "/api/config"): update_settings,
}
