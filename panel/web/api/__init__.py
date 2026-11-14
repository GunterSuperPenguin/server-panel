from . import control, files, locale, servers, settings, workshop

ROUTES = {**servers.ROUTES, **control.ROUTES, **settings.ROUTES, **locale.ROUTES, **files.ROUTES, **workshop.ROUTES}
