from ...locales import LANGUAGES, ui_messages
from ..request import Request


def get_locale(req: Request):
    return {
        "lang": req.locale,
        "languages": [{"code": code, "name": name} for code, name in LANGUAGES.items()],
        "messages": ui_messages(req.locale),
    }


ROUTES = {
    ("GET", "/api/locale"): get_locale,
}
