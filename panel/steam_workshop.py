"""Read and cache addon metadata from Steam’s public Workshop pages."""
import json
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse, urljoin
from urllib.request import Request, urlopen

from .errors import LocalizedError
from .workshop import parse_ids

TAGS = ('Addon', 'Gamemode', 'Map', 'Weapon', 'Vehicle', 'NPC', 'Tool', 'Effects', 'Model', 'ServerContent')
SORTS = {'popular': 'trend', 'recent': 'mostrecent', 'rated': 'toprated'}
_cache = {}
_lock = threading.Lock()


class Element:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(c.text() if isinstance(c, Element) else c for c in self.children)

    def find(self, cls=None, tag=None, id=None):
        for child in self.children:
            if isinstance(child, Element):
                if ((cls is None or cls in child.attrs.get('class', '').split())
                        and (tag is None or tag == child.tag) and (id is None or id == child.attrs.get('id'))):
                    yield child
                yield from child.find(cls, tag, id)


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag == 'br':
            self.stack[-1].children.append('\n')
        if tag not in ('img', 'br', 'hr', 'meta', 'link', 'input', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'):
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                if tag in ('p', 'div', 'li'):
                    self.stack[i].children.append('\n')
                del self.stack[i:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def first(root, cls=None, tag=None, id=None):
    return next(root.find(cls, tag, id), Element())


def fetch_page(path, params, timeout=12):
    url = 'https://steamcommunity.com/' + path + '?' + urlencode(params, doseq=True)
    with _lock:
        hit = _cache.get(url)
        if hit and hit[0] > time.monotonic():
            return hit[1]
    try:
        request = Request(url, headers={'User-Agent': 'GModLocalPanel/1.0', 'Accept-Language': 'en-US,en;q=0.9'})
        with urlopen(request, timeout=timeout) as response:
            if urlparse(response.geturl()).hostname != 'steamcommunity.com':
                raise ValueError('Unexpected redirect')
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('Oversize response')
        html = raw.decode('utf-8', errors='replace')
    except (URLError, OSError, ValueError):
        raise LocalizedError('err-steam-offline', status=502) from None
    with _lock:
        if len(_cache) >= 128:
            _cache.pop(next(iter(_cache)))
        _cache[url] = (time.monotonic() + 120, html)
    return html


def image_url(value):
    return value if isinstance(value, str) and urlparse(value).scheme == 'https' else ''


def normalize(item, authors=None):
    stars = item.get('star_rating', -1)
    return {
        'wsid': str(item['publishedfileid']), 'title': item.get('title', ''),
        'author': (authors or {}).get(str(item.get('creator')), str(item.get('creator', ''))),
        'image': image_url(item.get('preview_url')), 'description': item.get('short_description', ''),
        'tags': [t['tag'] for t in item.get('tags', []) if isinstance(t, dict) and 'tag' in t],
        'size': int(item.get('file_size', 0)), 'subscriptions': int(item.get('subscriptions', 0)),
        'rating': stars / 5 if stars >= 0 else None, 'updated': int(item.get('time_updated', 0)),
        'previews': [image_url(p.get('url')) for p in item.get('previews', []) if p.get('preview_type', 0) == 0],
    }


def embedded_data(value, depth=0):
    """Unpack Steam SSR loader data, including nested JSON strings, never JS."""
    if depth > 20:
        return
    if isinstance(value, str) and value.startswith(('{', '[')):
        try:
            yield from embedded_data(json.loads(value), depth + 1)
        except ValueError:
            pass
    elif isinstance(value, dict):
        yield value
        for child in value.values():
            yield from embedded_data(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from embedded_data(child, depth + 1)


def parse_search(html, page):
    root = Page(html).root
    ssr = first(root, id='valve-ssr-data').text()
    try:
        data = next(d for d in embedded_data(json.loads(ssr)) if 'results' in d and 'total_count' in d)
        authors = {p['public_data']['steamid']: p['public_data'].get('persona_name', '')
                   for p in data.get('creator_player_link_details', []) if 'public_data' in p}
        items = [normalize(item, authors) for item in data['results']
                 if item.get('consumer_appid') == 4000 and item.get('file_type', 0) != 2]
        return {'items': items, 'total': int(data['total_count']), 'page': int(data.get('current_page', page)), 'page_size': 30}
    except (ValueError, TypeError, KeyError, StopIteration):
        raise LocalizedError('err-steam-page', status=502) from None


def required_items(root):
    ids = []
    sections = list(root.find(id='RequiredItems')) + list(root.find('requiredItemsContainer'))
    for section in sections:
        for link in section.find(tag='a'):
            url = urlparse(urljoin('https://steamcommunity.com/', link.attrs.get('href', '')))
            if url.hostname not in ('steamcommunity.com', 'www.steamcommunity.com') or url.path.rstrip('/') not in ('/sharedfiles/filedetails', '/workshop/filedetails'):
                continue
            value = parse_qs(url.query).get('id', [''])[0]
            try:
                wsid = parse_ids(value)[0]
            except LocalizedError:
                continue
            if wsid not in ids:
                ids.append(wsid)
    return ids


def details(wsid, timeout=12):
    ids = parse_ids(wsid)
    if len(ids) != 1:
        raise LocalizedError('err-workshop-id')
    html = fetch_page('sharedfiles/filedetails/', {'id': ids[0], 'l': 'english'}, timeout=timeout)
    root = Page(html).root
    title = first(root, 'workshopItemTitle').text().strip()
    description = first(root, 'workshopItemDescription')
    app_links = [a for a in root.find(tag='a') if re.search(r'(?:/app/4000(?:/|$)|[?&]appid=4000(?:&|$))', a.attrs.get('href', ''))]
    if not title or not description.children or not app_links:
        raise LocalizedError('err-steam-item', status=404)
    stats = [n.text().strip() for n in root.find('detailsStatRight')]
    size = 0
    if stats:
        match = re.search(r'([\d.,]+)\s*(B|KB|MB|GB)', stats[0], re.I)
        if match:
            size = int(float(match[1].replace(',', '')) * 1024 ** ('B', 'KB', 'MB', 'GB').index(match[2].upper()))
    updated = 0
    if len(stats) >= 2:
        value = stats[-1]
        for fmt in ('%d %b, %Y @ %I:%M%p', '%d %b @ %I:%M%p'):
            try:
                date = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                if date.year == 1900:
                    date = date.replace(year=datetime.now(timezone.utc).year)
                updated = int(date.timestamp())
                break
            except ValueError:
                pass
    subscribers = 0
    for row in first(root, 'stats_table').find(tag='tr'):
        cells = list(row.find(tag='td'))
        if len(cells) == 2 and 'Current Subscribers' in cells[1].text():
            subscribers = int(re.sub(r'\D', '', cells[0].text()) or 0)
    previews = []
    match = re.search(r'var\s+rgFullScreenshotURLs\s*=\s*\[(.*?)\];', html, re.S)
    if match:
        previews = [image_url(url) for url in re.findall(r"'url'\s*:\s*'([^']+)'", match[1])]
    thumbnail = first(root, tag='img', id='previewImage').attrs.get('src', '')
    stars = re.search(r'([0-5])-star', html)
    author_node = first(root, 'friendBlockContent')
    author = ''.join(c for c in author_node.children if isinstance(c, str)).strip()
    return {'wsid': ids[0], 'title': title, 'description': description.text().strip(),
            'author': author, 'image': image_url(thumbnail) or next(iter(previews), ''),
            'previews': previews, 'tags': [a.text().strip() for block in root.find('workshopTags') for a in block.find(tag='a')],
            'required_items': required_items(root),
            'size': size, 'subscriptions': subscribers, 'rating': int(stars[1]) / 5 if stars else None, 'updated': updated}


def search(query, tags, sort, page):
    if len(query) > 200 or sort not in SORTS or any(tag not in TAGS for tag in tags):
        raise LocalizedError('err-bad-request')
    try:
        page = int(page)
    except (ValueError, TypeError):
        raise LocalizedError('err-bad-request') from None
    if not 1 <= page <= 1000:
        raise LocalizedError('err-bad-request')
    if query.strip().isdigit() or query.strip().startswith(('https://', 'http://')):
        return {'items': [details(query.strip())], 'total': 1, 'page': 1, 'page_size': 30}
    params = {'appid': 4000, 'searchtext': query, 'browsesort': SORTS[sort], 'actualsort': SORTS[sort],
              'section': 'readytouseitems', 'p': page, 'numperpage': 30, 'days': 7, 'l': 'english',
              'requiredtags[]': list(dict.fromkeys(tags))}
    return parse_search(fetch_page('workshop/browse/', params), page)
