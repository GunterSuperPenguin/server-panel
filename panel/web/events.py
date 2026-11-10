import json


def _line(line, l10n):
    text = line["text"] if "text" in line else l10n.format_value(line["key"], line["params"])
    return {"kind": line["kind"], "text": text}


def encode(msg, l10n):
    if msg["type"] == "line":
        msg = {"type": "line", "line": _line(msg["line"], l10n)}
    elif msg["type"] == "history":
        msg = {"type": "history", "lines": [_line(line, l10n) for line in msg["lines"]]}
    return json.dumps(msg, ensure_ascii=False)
