import threading

from ..request import EventStream, Request


def events(req: Request):
    return EventStream(req.instance().hub)


def start(req: Request):
    return {"ok": req.instance().server.start()}


def stop(req: Request):
    server = req.instance().server
    threading.Thread(target=server.stop, daemon=True).start()
    return {"ok": True}


def restart(req: Request):
    req.instance().server.restart()
    return {"ok": True}


def command(req: Request):
    text = str(req.data.get("command", "")).strip()
    if text:
        req.instance().server.command(text)
    return {"ok": True}


ROUTES = {
    ("GET", "/api/events"): events,
    ("POST", "/api/start"): start,
    ("POST", "/api/stop"): stop,
    ("POST", "/api/restart"): restart,
    ("POST", "/api/command"): command,
}
