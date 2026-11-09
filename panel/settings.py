import json

from .config import DEFAULT_SETTINGS, SAFE_VALUE_RE, server_path


def load_settings(name):
    cfg = dict(DEFAULT_SETTINGS)
    try:
        cfg.update(json.loads((server_path(name) / "panel.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save_settings(name, cfg):
    (server_path(name) / "panel.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_settings(name, data):
    cfg = load_settings(name)
    for key, title in (("map", "Map"), ("gamemode", "Gamemode")):
        value = str(data.get(key, cfg[key])).strip()
        if not SAFE_VALUE_RE.match(value):
            raise ValueError(f"{title}: only letters, digits, _ . - are allowed")
        cfg[key] = value
    collection = str(data.get("workshop_collection", "")).strip()
    if collection and not collection.isdigit():
        raise ValueError("Workshop collection ID must contain digits only")
    cfg["workshop_collection"] = collection
    for key, title, lo, hi in (("maxplayers", "Max players", 1, 128), ("port", "Port", 1024, 65535)):
        try:
            value = int(data.get(key, cfg[key]))
        except (TypeError, ValueError):
            raise ValueError(f"{title} must be a number")
        if not lo <= value <= hi:
            raise ValueError(f"{title} must be between {lo} and {hi}")
        cfg[key] = value
    cfg["update_on_start"] = bool(data.get("update_on_start"))
    cfg["auto_restart"] = bool(data.get("auto_restart"))
    return cfg
