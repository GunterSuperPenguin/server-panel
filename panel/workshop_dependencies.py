"""Bounded breadth-first traversal of public Garry's Mod Required Items."""
from collections import deque
import time

from .errors import LocalizedError
from .steam_workshop import details

MAX_ITEMS = 100
MAX_DEPTH = 12
MAX_SECONDS = 45
MIN_LOOKUP_INTERVAL = 0.1


def resolve(ids):
    # Schedule each ID just once, including roots that also occur as dependencies.
    visited = set(ids)
    if len(visited) > MAX_ITEMS:
        raise LocalizedError('err-dependencies-limit')
    queue = deque((wsid, 0) for wsid in ids)
    items, warnings = [], []
    deadline = time.monotonic() + MAX_SECONDS
    next_lookup = time.monotonic()
    while queue:
        delay = next_lookup - time.monotonic()
        if delay > 0:
            time.sleep(min(delay, max(0, deadline - time.monotonic())))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LocalizedError('err-dependencies-limit')
        next_lookup = time.monotonic() + MIN_LOOKUP_INTERVAL
        wsid, depth = queue.popleft()
        try:
            item = details(wsid, timeout=min(12, remaining))
        except LocalizedError as error:
            warnings.append({'wsid': wsid, 'key': 'dependencies-unavailable' if error.key == 'err-steam-item' else 'dependencies-fetch-failed'})
            continue
        items.append({'wsid': wsid, 'label': item['title'][:300], 'enabled': True})
        for child in item.get('required_items', []):
            if child in visited:
                continue
            if depth >= MAX_DEPTH or len(visited) >= MAX_ITEMS:
                raise LocalizedError('err-dependencies-limit')
            visited.add(child)
            queue.append((child, depth + 1))
    if time.monotonic() > deadline:
        raise LocalizedError('err-dependencies-limit')
    return items, warnings
