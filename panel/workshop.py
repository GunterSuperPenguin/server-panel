"""Panel-local Workshop presets and SRCDS KeyValues output."""
import json
import re
import threading
import uuid
from urllib.parse import parse_qs, urlparse

from .config import server_path
from .errors import LocalizedError

_lock = threading.RLock()


def parse_ids(text):
    if not isinstance(text, str):
        raise LocalizedError('err-workshop-id')
    result = []
    for token in re.split(r'[\s,;]+', text.strip()):
        if not token:
            continue
        if not re.fullmatch(r'[0-9]+', token):
            url = urlparse(token)
            if url.scheme not in ('http', 'https') or url.hostname not in ('steamcommunity.com', 'www.steamcommunity.com'):
                raise LocalizedError('err-workshop-id')
            token = parse_qs(url.query).get('id', [''])[0]
        if not re.fullmatch(r'[0-9]{1,20}', token) or not 0 < int(token) < 2**64:
            raise LocalizedError('err-workshop-id')
        token = str(int(token))
        if token not in result:
            result.append(token)
    if not result:
        raise LocalizedError('err-workshop-id')
    return result


def render(addons):
    lines = ['"my_workshop_addons"', '{']
    for index, addon in enumerate((a for a in addons if a['enabled']), 1):
        lines.extend([f'    "{index}"', '    {', f'        "wsid" "{addon["wsid"]}"', '    }'])
    return '\n'.join(lines + ['}', ''])


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def paths(name):
    root = server_path(name)
    return root / 'workshop.json', root / 'garrysmod/cfg/srcds_workshop_ids.txt'


def load(name):
    storage, cfg = paths(name)
    if storage.exists():
        return json.loads(storage.read_text(encoding='utf-8'))
    ids = []
    if cfg.exists():
        content = re.sub(r'//[^\n]*', '', cfg.read_text(encoding='utf-8-sig'))
        for value in re.findall(r'"wsid"\s*"([0-9]+)"', content, re.I):
            for wsid in parse_ids(value):
                if wsid not in ids:
                    ids.append(wsid)
    state = {'active': 'default', 'collections': [{'id': 'default', 'name': '', 'addons': [
        {'wsid': wsid, 'label': '', 'enabled': True} for wsid in ids]}]}
    persist(name, state)
    return state


def persist(name, state):
    storage, cfg = paths(name)
    active = next(c for c in state['collections'] if c['id'] == state['active'])
    atomic_write(cfg, render(active['addons']))
    atomic_write(storage, json.dumps(state, ensure_ascii=False, indent=2))


def manage(name, data=None):
    resolved = None
    if data is not None and data.get('action') == 'add':
        ids = parse_ids(data.get('ids'))
        with _lock:
            try:
                initial = load(name)
            except (OSError, ValueError, KeyError, StopIteration):
                raise LocalizedError('err-workshop-storage') from None
            target = data.get('collection', initial['active'])
            if not any(c['id'] == target for c in initial['collections']):
                raise LocalizedError('err-workshop-collection')
        data = {**data, 'collection': target}
        # Network traversal must not hold the storage lock. Reload the preset
        # after traversal so concurrent edits are preserved at commit time.
        from .workshop_dependencies import resolve
        resolved, warnings = resolve(ids)
    with _lock:
        try:
            state = load(name)
            if data is None:
                return state
            action = data.get('action')
            collection = next((c for c in state['collections'] if c['id'] == data.get('collection', state['active'])), None)
            if action in ('create', 'rename'):
                title = data.get('name')
                if not isinstance(title, str) or not title.strip() or len(title.strip()) > 80:
                    raise LocalizedError('err-workshop-name')
            if action == 'create':
                collection = {'id': uuid.uuid4().hex, 'name': title.strip(), 'addons': []}
                state['collections'].append(collection)
                state['active'] = collection['id']
            else:
                if collection is None:
                    raise LocalizedError('err-workshop-collection')
                if action == 'rename':
                    collection['name'] = title.strip()
                elif action == 'activate':
                    state['active'] = collection['id']
                elif action == 'delete':
                    if len(state['collections']) == 1:
                        raise LocalizedError('err-workshop-last')
                    state['collections'].remove(collection)
                    if state['active'] == collection['id']:
                        state['active'] = state['collections'][0]['id']
                elif action == 'add':
                    existing = {a['wsid'] for a in collection['addons']}
                    added = [item for item in resolved if item['wsid'] not in existing]
                    collection['addons'].extend(added)
                    addition = {
                        'roots': [a for a in added if a['wsid'] in ids],
                        'dependencies': [a for a in added if a['wsid'] not in ids],
                        'warnings': warnings,
                    }
                elif action in ('toggle', 'remove'):
                    addon = next((a for a in collection['addons'] if a['wsid'] == data.get('wsid')), None)
                    if addon is None:
                        raise LocalizedError('err-workshop-id')
                    if action == 'remove':
                        collection['addons'].remove(addon)
                    else:
                        if not isinstance(data.get('enabled'), bool):
                            raise LocalizedError('err-bad-request')
                        addon['enabled'] = data['enabled']
                else:
                    raise LocalizedError('err-bad-request')
            persist(name, state)
            if resolved is not None:
                return {**state, 'addition': addition}
            return state
        except (OSError, ValueError, KeyError, StopIteration):
            raise LocalizedError('err-workshop-storage')
