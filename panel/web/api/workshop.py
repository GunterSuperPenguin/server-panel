from ...steam_workshop import search, details
from ...workshop import manage


def get_workshop(req):
    return manage(req.instance().name)


def update_workshop(req):
    return manage(req.instance().name, req.data)


def browse_workshop(req):
    q = req.query
    return search(q.get('q', [''])[0], [tag for tag in q.get('tags', [''])[0].split(',') if tag], q.get('sort', ['popular'])[0], q.get('page', ['1'])[0])


def workshop_details(req):
    return details(req.query.get('id', [''])[0])


ROUTES = {
    ('GET', '/api/workshop/search'): browse_workshop,
    ('GET', '/api/workshop/details'): workshop_details,
    ('GET', '/api/workshop'): get_workshop,
    ('POST', '/api/workshop'): update_workshop,
}
