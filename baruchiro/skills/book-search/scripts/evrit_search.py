#!/usr/bin/env python3
"""
Deterministic, read-only e-vrit verification; Python standard library only.
Verifies e-vrit.co.il product pages by parsing JSON-LD structured data.
Supports: title, author, price, availability, rating, basic format info.

LIMITATIONS:
- e-vrit uses client-side rendering (Next.js). Search requires JavaScript;
  no public search API. This script CANNOT reliably search without a browser.
- Detailed format pricing (digital vs print original/final prices) for the
  MAIN product is not available in static HTML; only the JSON-LD offer price
  (32 ILS) and InStock availability are reliably available.
- Library marker "ספריה ציבורית דיגיטלית" requires JavaScript rendering
  and is not available in static HTML.
- Recommended/related products' format pricing IS in the page but not
  reliably matched to the main product.
Use case: verify a known product URL, or parse an author page for known books.
"""
import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin, urlparse, quote
from urllib.request import Request, urlopen

BASE = 'https://www.e-vrit.co.il/'
UA = 'Mozilla/5.0 (compatible; book-search/0.2.0; +https://github.com/baruchiro/skills)'

def fetch(url, max_retries=3):
    from urllib.parse import urlparse, quote
    p = urlparse(url)
    path = quote(p.path, safe='/')
    url = p._replace(path=path).geturl()
    for attempt in range(max_retries):
        try:
            with urlopen(Request(url, headers={'User-Agent': UA}), timeout=30) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError('fetch failed')

def extract_json_ld(source):
    blocks = []
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source, re.S):
        try:
            data = json.loads(m.group(1).strip())
            blocks.append(data)
        except json.JSONDecodeError:
            pass
    return blocks

def find_book_json_ld(blocks):
    for block in blocks:
        items = block if isinstance(block, list) else [block]
        for item in items:
            if isinstance(item, dict):
                types = item.get('@type')
                if isinstance(types, str):
                    types = [types]
                if types and any(t in ('Book', 'Product') for t in types):
                    return item
    return None

def parse_product_page(html_text, url):
    blocks = extract_json_ld(html_text)
    book = find_book_json_ld(blocks)
    if not book:
        raise ValueError('No Book/Product JSON-LD found on product page')

    title = book.get('name', '')
    description = book.get('description', '')

    authors = []
    author_data = book.get('author')
    if isinstance(author_data, list):
        for a in author_data:
            if isinstance(a, dict) and a.get('name'):
                authors.append(a['name'])
            elif isinstance(a, str):
                authors.append(a)
    elif isinstance(author_data, dict) and author_data.get('name'):
        authors.append(author_data['name'])

    offers = book.get('offers', [])
    if isinstance(offers, dict):
        offers = [offers]

    price = None
    price_currency = 'ILS'
    availability = None
    sku = None
    for offer in offers:
        if isinstance(offer, dict):
            if offer.get('price') is not None:
                price = offer['price']
            if offer.get('priceCurrency'):
                price_currency = offer['priceCurrency']
            if offer.get('availability'):
                availability = offer['availability']
            if offer.get('sku'):
                sku = offer['sku']

    rating = None
    review_count = None
    aggregate = book.get('aggregateRating')
    if isinstance(aggregate, dict):
        rating = aggregate.get('ratingValue')
        review_count = aggregate.get('reviewCount')

    product_id = sku
    if not product_id:
        m = re.search(r'/product/(\d+)/', url)
        if m:
            product_id = m.group(1)

    # Note: detailed format pricing (digital/print original/final) for the
    # main product is not available in static HTML; only the JSON-LD offer
    # price and InStock status are reliably available.
    # Recommended products' format pricing appears in the page but cannot
    # be reliably matched to the main product.

    return {
        'id': product_id,
        'title': title,
        'description': description,
        'authors': sorted(set(authors)),
        'url': url,
        'price': price,
        'price_currency': price_currency,
        'availability': availability,
        'sku': sku,
        'rating': rating,
        'review_count': review_count,
        'format_note': 'Detailed format pricing (digital/print original/final) for the main product is not available in static HTML. Only JSON-LD offer price and InStock status are reliably available.',
        'library_marker': None,
        'library_marker_note': 'Not available in static HTML; requires JavaScript rendering.',
    }

def parse_author_page(html_text, url):
    product_ids = set()
    for m in re.finditer(r'/product/(\d+)/', html_text):
        product_ids.add(m.group(1))
    return sorted(product_ids)

def search_via_ddg(query, max_results=10):
    encoded = quote(query + ' site:e-vrit.co.il/product/')
    url = f'https://duckduckgo.com/html/?q={encoded}'
    source = fetch(url)
    results = []
    for m in re.finditer(r'<a[^>]*href="(https://www\.e-vrit\.co\.il/product/[^"]*)"[^>]*>', source):
        url = html.unescape(m.group(1))
        pid_match = re.search(r'/product/(\d+)/', url)
        if pid_match:
            results.append({'url': url, 'id': pid_match.group(1)})
        if len(results) >= max_results:
            break
    return results

def main():
    parser = argparse.ArgumentParser(description='Verify e-vrit.co.il product pages')
    parser.add_argument('input', help='Product URL, author URL, or search query')
    parser.add_argument('--mode', choices=['product', 'author', 'search'], default='product',
                        help='Input type: product URL, author URL, or search query')
    parser.add_argument('--max-results', type=int, default=10)
    args = parser.parse_args()

    if args.mode == 'product':
        url = args.input
        if not url.startswith('http'):
            url = urljoin(BASE, 'product/' + args.input + '/')
        html_text = fetch(url)
        result = parse_product_page(html_text, url)
    elif args.mode == 'author':
        url = args.input
        if not url.startswith('http'):
            url = urljoin(BASE, 'author/' + args.input + '/')
        html_text = fetch(url)
        product_ids = parse_author_page(html_text, url)
        products = []
        for pid in product_ids[:args.max_results]:
            purl = urljoin(BASE, f'product/{pid}/')
            try:
                phtml = fetch(purl)
                products.append(parse_product_page(phtml, purl))
                time.sleep(0.3)
            except Exception as e:
                products.append({'id': pid, 'error': str(e)})
        result = {'author_url': url, 'products': products}
    else:  # search
        results = search_via_ddg(args.input, args.max_results)
        products = []
        for r in results:
            try:
                phtml = fetch(r['url'])
                products.append(parse_product_page(phtml, r['url']))
                time.sleep(0.5)
            except Exception as e:
                products.append({'id': r['id'], 'error': str(e)})
        result = {'query': args.input, 'products': products}

    print(json.dumps({
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'mode': args.mode,
        'input': args.input,
        **result
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()