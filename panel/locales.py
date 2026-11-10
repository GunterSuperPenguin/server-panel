from functools import lru_cache
from pathlib import Path

from fluent.runtime import FluentBundle, FluentLocalization, FluentResourceLoader
from fluent.syntax import ast

L10N_DIR = Path(__file__).parent / "locales"
UI_FILES = ["header.ftl", "console.ftl", "settings.ftl", "dialog.ftl"]
SERVER_FILES = ["messages.ftl"]
FILES = UI_FILES + SERVER_FILES
LANGUAGES = {"ru": "Русский", "en": "English"}
SUPPORTED = list(LANGUAGES)
DEFAULT = "en"

_loader = FluentResourceLoader(str(L10N_DIR / "{locale}"))


def _chain(locale):
    return [DEFAULT] if locale == DEFAULT else [DEFAULT, locale]


@lru_cache(maxsize=None)
def get_l10n(locale: str) -> FluentLocalization:
    locales = [locale, DEFAULT] if locale != DEFAULT else [DEFAULT]
    return FluentLocalization(locales, FILES, _loader, use_isolating=False)


def resolve_locale(requested, accept_language=""):
    if requested in SUPPORTED:
        return requested
    for part in accept_language.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED:
            return code
    return DEFAULT


@lru_cache(maxsize=None)
def ui_messages(locale: str) -> dict:
    messages = {}
    for code in _chain(locale):
        bundle = FluentBundle([code], use_isolating=False)
        ids = []
        for resources in _loader.resources(code, UI_FILES):
            for resource in resources:
                bundle.add_resource(resource)
                ids += [e.id.name for e in resource.body if isinstance(e, ast.Message)]
        for message_id in ids:
            message = bundle.get_message(message_id)
            if message.value:
                messages[message_id] = bundle.format_pattern(message.value)[0]
            for name, pattern in message.attributes.items():
                messages[f"{message_id}.{name}"] = bundle.format_pattern(pattern)[0]
    return messages
