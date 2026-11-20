#!/usr/bin/env python3
"""Read-only public overdrive search. See references/overdrive.md."""
import json
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlencode
from _catalog_common import (CatalogError, PublicReader, OD, exact_candidate)
from _search_common import run_cli


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


def search(query, mode='title', max_pages=3, reader=None):
    provider = 'overdrive'
    if mode not in ('title', 'author'):
        raise ValueError('Unknown title/author mode')
    if not query.strip() or len(query) > 100 or not 1 <= max_pages <= 10:
        raise ValueError('Query must be 1-100 characters; max-pages must be 1-10')
    reader = reader or PublicReader()
    result = {'provider': provider, 'query': query, 'mode': mode,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'account_state': 'signed_out',
              'personal_entitlement': 'unverified', 'complete': False, 'pages': [], 'products': [], 'errors': []}
    try:
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
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        result['complete'] = False
    for item in result['products']:
        item['query_exact_match'] = exact_candidate(item, query, mode)
    result['count'] = len(result['products'])
    return result


if __name__ == '__main__':
    raise SystemExit(run_cli('overdrive', search))
