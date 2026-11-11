from . import control, files, locale, servers, settings

ROUTES = {**servers.ROUTES, **control.ROUTES, **settings.ROUTES, **locale.ROUTES, **files.ROUTES}
