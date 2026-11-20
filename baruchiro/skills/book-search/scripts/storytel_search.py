#!/usr/bin/env python3
"""Read-only public storytel search. See references/storytel.md."""
import json
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse
from _catalog_common import (CatalogError, PublicReader, ST, exact_candidate)
from _search_common import run_cli


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


def search(query, mode='title', max_pages=3, reader=None):
    provider = 'storytel'
    if mode not in ('title', 'author'):
        raise ValueError('Unknown title/author mode')
    if not query.strip() or len(query) > 100 or not 1 <= max_pages <= 10:
        raise ValueError('Query must be 1-100 characters; max-pages must be 1-10')
    reader = reader or PublicReader()
    result = {'provider': provider, 'query': query, 'mode': mode,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'account_state': 'signed_out',
              'personal_entitlement': 'unverified', 'complete': False, 'pages': [], 'products': [], 'errors': []}
    seen = set()
    try:
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


if __name__ == '__main__':
    raise SystemExit(run_cli('storytel', search))
