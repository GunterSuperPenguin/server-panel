import mimetypes

from ..config import STATIC_DIR


def read_static(url_path):
    relative = url_path.lstrip("/") or "index.html"
    target = (STATIC_DIR / relative).resolve()
    if STATIC_DIR not in target.parents or not target.is_file():
        return None
    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type.endswith("javascript"):
        content_type += "; charset=utf-8"
    return target.read_bytes(), content_type
