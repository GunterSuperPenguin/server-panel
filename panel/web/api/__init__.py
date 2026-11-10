from . import control, locale, servers, settings

ROUTES = {**servers.ROUTES, **control.ROUTES, **settings.ROUTES, **locale.ROUTES}
