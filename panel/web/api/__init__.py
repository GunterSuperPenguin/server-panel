from . import control, servers, settings

ROUTES = {**servers.ROUTES, **control.ROUTES, **settings.ROUTES}
