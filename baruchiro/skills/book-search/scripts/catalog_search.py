#!/usr/bin/env python3
"""Small, read-only public catalog searches. Python standard library only.

No cookies, credentials, playback, loans or account mutations. Public records
are candidates, never proof of personal library/subscription entitlement.
"""
import argparse
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

UA = 'book-search/0.2.3 (+https://github.com/baruchiro/skills)'
HOSTS = {'telaviv.overdrive.com', 'api.storytel.net'}
OD = 'https://telaviv.overdrive.com'
ST = 'https://api.storytel.net/search/client/web'


class CatalogError(ValueError):
    pass


def safe_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None, 443) or p.username or p.password:
        raise CatalogError('Unapproved catalog URL')
    allowed_paths = {'telaviv.overdrive.com': {'/robots.txt', '/search', '/search/title'},
                     'api.storytel.net': {'/robots.txt', '/search/client/web'}}
    if p.path not in allowed_paths[p.hostname]:
        raise CatalogError('Unapproved catalog path')
    if p.hostname == 'telaviv.overdrive.com' and 'page' in parse_qs(p.query):
        raise CatalogError('OverDrive page-parameter pagination refused')
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        if urlparse(req.full_url).hostname != urlparse(newurl).hostname:
            raise CatalogError('Cross-host redirect refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicReader:
    """Sequential GETs only; robots enforced, bounded bytes, no retries."""
    def __init__(self, opener=None, clock=time.monotonic, sleep=time.sleep):
        self.opener = opener or build_opener(SafeRedirect())
        self.rules = {}
        self.last = {}
        self.clock, self.sleep = clock, sleep

    def _read(self, url, delay=2):
        safe_url(url)
        host = urlparse(url).hostname
        elapsed = self.clock() - self.last.get(host, float('-inf'))
        if elapsed < delay:
            self.sleep(delay - elapsed)
        self.last[host] = self.clock()
        request = Request(url, headers={'User-Agent': UA, 'Accept': 'application/json,text/html,text/plain'})
        with self.opener.open(request, timeout=30) as response:
            safe_url(response.geturl())
            data = response.read(8_000_001)
            if len(data) > 8_000_000:
                raise CatalogError('Response exceeds 8 MB limit')
            return data.decode('utf-8')

    def get(self, url):
        safe_url(url)
        p = urlparse(url)
        origin = f'https://{p.hostname}'
        if origin not in self.rules:
            robot_url = origin + '/robots.txt'
            try:
                body = self._read(robot_url)
            except HTTPError as exc:
                if exc.code != 404:
                    raise
                body = ''  # Missing robots file, not access denied.
            robot = RobotFileParser(robot_url)
            robot.parse(body.splitlines())
            self.rules[origin] = robot
        robot = self.rules[origin]
        if not robot.can_fetch(UA, url):
            raise CatalogError('robots.txt disallows this URL')
        return self._read(url, max(2, robot.crawl_delay(UA) or 0))


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())


def exact_candidate(item, query, mode):
    fields = [item['title']] if mode == 'title' else item['authors']
    return any(normalized(s) == normalized(query) for s in fields)


def parse_overdrive(source):
    """Use titleCollection, not mediaItems (which may contain related records)."""
    match = re.search(r'window\.OverDrive\.titleCollection\s*=\s*', source)
    if not match:
        raise CatalogError('OverDrive titleCollection missing; not an empty result')
    try:
        rows, _ = json.JSONDecoder().raw_decode(source[match.end():])
    except json.JSONDecodeError as exc:
        raise CatalogError('Malformed OverDrive titleCollection') from exc
    if not isinstance(rows, list):
        raise CatalogError('OverDrive titleCollection is not a list')
    plain = unescape(re.sub('<[^>]+>', ' ', source))
    total_match = re.search(r'Showing\s+[\d,]+\s*[-–]\s*[\d,]+\s+of\s+([\d,]+)\s+results', plain)
    empty = re.search(r"couldn.t find any matches", plain, re.I)
    if total_match:
        total = int(total_match[1].replace(',', ''))
    elif empty and not rows:
        total = 0
    else:
        raise CatalogError('OverDrive result count missing; layout may have changed')
    products = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get('id', '')).isdigit() or not isinstance(row.get('title'), str):
            raise CatalogError('Malformed OverDrive record')
        creators = row.get('creators')
        if not isinstance(creators, list):
            raise CatalogError('OverDrive creators missing')
        available, owned = row.get('availableCopies'), row.get('ownedCopies')
        if type(available) is not int or type(owned) is not int or min(available, owned) < 0 or available > owned:
            raise CatalogError('OverDrive copy counts missing or inconsistent')
        state = 'available' if available > 0 else 'no_licensed_copies' if owned == 0 else 'hold' if row.get('isHoldable') is True else 'unavailable'
        products.append({
            'id': str(row['id']), 'title': row['title'],
            'authors': [c['name'] for c in creators if c.get('role') == 'Author' and isinstance(c.get('name'), str)],
            'contributors': [{'name': c.get('name'), 'role': c.get('role')} for c in creators],
            'languages': [v.get('id') for v in row.get('languages', [])],
            'format': row.get('type', {}).get('id'),
            'formats': [{'id': v.get('id'), 'isbn': v.get('isbn')} for v in row.get('formats', [])],
            'series': row.get('detailedSeries'), 'publisher': row.get('publisher', {}).get('name'),
            'url': OD + '/media/' + str(row['id']),
            'public_availability': state, 'available_copies': available, 'owned_copies': owned,
            'holds_count': row.get('holdsCount'), 'is_holdable': row.get('isHoldable'),
            'personal_entitlement': 'unverified',
        })
    if len(products) > total:
        raise CatalogError('OverDrive records exceed declared result count')
    return products, total


def parse_storytel(data):
    if not isinstance(data, dict) or not isinstance(data.get('items'), list) or type(data.get('totalCount')) is not int:
        raise CatalogError('Storytel search schema missing; not an empty result')
    if data['totalCount'] < 0:
        raise CatalogError('Negative Storytel result count')
    token = data.get('nextPageToken')
    if token is not None and not isinstance(token, (str, int)):
        raise CatalogError('Invalid Storytel page token')
    products = []
    for row in data['items']:
        if not isinstance(row, dict) or row.get('resultType') != 'book':
            raise CatalogError('Unexpected non-book in book-only search')
        if not str(row.get('id', '')).isdigit() or not isinstance(row.get('title'), str) or not isinstance(row.get('authors'), list) or not isinstance(row.get('formats'), list):
            raise CatalogError('Malformed Storytel book')
        url = row.get('shareUrl')
        parsed = urlparse(url or '')
        if parsed.scheme != 'https' or parsed.netloc != 'www.storytel.com' or not parsed.path.startswith('/il/books/'):
            raise CatalogError('Storytel Israel share URL missing or wrong market')
        products.append({
            'id': str(row['id']), 'title': row['title'],
            'authors': [c['name'] for c in row['authors'] if isinstance(c.get('name'), str)],
            'narrators': [c['name'] for c in row.get('narrators', []) if isinstance(c.get('name'), str)],
            'languages': [row.get('language')], 'series': row.get('seriesInfo'), 'duration': row.get('duration'),
            'formats': [{'id': f.get('id'), 'type': f.get('type'), 'released': f.get('isReleased'),
                         'locked': f.get('isLockedContent'), 'catalog_access': f.get('availabilityInfo', [])}
                        for f in row['formats']],
            'url': url, 'public_availability': 'catalog_record', 'personal_entitlement': 'unverified',
        })
    return products, data['totalCount'], str(token) if token is not None else None


def search(provider, query, mode='title', max_pages=3, reader=None):
    if provider not in ('overdrive', 'storytel') or mode not in ('title', 'author'):
        raise ValueError('Unknown provider or mode')
    if not query.strip() or len(query) > 100 or not 1 <= max_pages <= 10:
        raise ValueError('Query must be 1-100 characters; max-pages must be 1-10')
    reader = reader or PublicReader()
    result = {'provider': provider, 'query': query, 'mode': mode,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'account_state': 'signed_out',
              'personal_entitlement': 'unverified', 'complete': False, 'pages': [], 'products': [], 'errors': []}
    seen = set()
    try:
        if provider == 'overdrive':
            params = {'query': query} if mode == 'title' else {'creator': query, 'sortBy': 'newlyadded'}
            url = OD + ('/search?' if mode == 'title' else '/search/title?') + urlencode(params)
            result['attempted_url'] = url
            products, total = parse_overdrive(reader.get(url))
            result['pages'].append(url)
            result['products'] = products
            result['total'] = total
            result['complete'] = len(products) == total
            result['coverage'] = 'public_collection_only; login can expose more titles/copies'
            if not result['complete']:
                result['errors'].append('More results exist; page-parameter pagination is disallowed by observed robots.txt. Narrow the query; do not bypass.')
        else:
            token = None
            tokens = set()
            for _ in range(max_pages):
                params = {'query': query, 'store': 'STHP-IL', 'searchFor': 'books', 'includeFormats': 'abook,ebook'}
                if token is not None:
                    params['page'] = token
                url = ST + '?' + urlencode(params)
                result['attempted_url'] = url
                raw = json.loads(reader.get(url))
                products, total, next_token = parse_storytel(raw)
                result['pages'].append(url)
                if 'total' in result and result['total'] != total:
                    raise CatalogError('Storytel total changed during pagination')
                result['total'] = total
                for item in products:
                    if item['id'] not in seen:
                        result['products'].append(item)
                        seen.add(item['id'])
                if len(seen) > total:
                    raise CatalogError('Storytel records exceed declared result count')
                if next_token is None:
                    if len(seen) != total:
                        raise CatalogError('Storytel count mismatch without next page')
                    result['complete'] = True
                    break
                if next_token == token or next_token in tokens:
                    raise CatalogError('Storytel repeated page token')
                tokens.add(next_token)
                # Tokens are opaque: never increment or invent them.
                if not products:
                    raise CatalogError('Storytel empty page with continuation')
                token = next_token
            if not result['complete']:
                result['errors'].append('Pagination limit reached; results incomplete')
            result['coverage'] = 'Israel public catalog; subscription markers do not confirm personal plan access'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        result['complete'] = False
    for item in result['products']:
        item['query_exact_match'] = exact_candidate(item, query, mode)
    result['count'] = len(result['products'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('provider', choices=['overdrive', 'storytel'])
    parser.add_argument('query')
    parser.add_argument('--mode', choices=['title', 'author'], default='title', help='Author mode searches book records by author text, not an author directory')
    parser.add_argument('--max-pages', type=int, default=3)
    parser.add_argument('--output', type=Path, help='Optional JSON output outside the package')
    args = parser.parse_args()
    try:
        result = search(args.provider, args.query, args.mode, args.max_pages)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0 if result['complete'] else 2


if __name__ == '__main__':
    sys.exit(main())
