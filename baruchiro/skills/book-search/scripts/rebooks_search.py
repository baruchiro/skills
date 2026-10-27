"""Deterministic, read-only Rebooks search; Python standard library only."""
import argparse
import html
from html.parser import HTMLParser
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin, urlparse, quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'https://rebooks.org.il/'

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text) if c.isalnum()).casefold()

def text_of(fragment):
    return html.unescape(re.sub(r'<[^>]+>', '', fragment)).strip()

def fetch(url):
    if urlparse(url).hostname != 'rebooks.org.il':
        raise ValueError('Only rebooks.org.il is allowed')
    url = quote(url, safe=':/?=&%+#')
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:
                return response.read().decode('utf-8')
        except HTTPError as error:
            if error.code not in (408, 425) and not 500 <= error.code < 600:
                raise
            if attempt == 2:
                raise
            time.sleep(1+attempt)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1+attempt)

class _ProductDivParser(HTMLParser):
    def __init__(self, source, predicate):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.predicate = predicate
        self.line_starts = [0]
        self.line_starts.extend(match.end() for match in re.finditer('\n', source))
        self.active = []
        self.blocks = []

    def _offset(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'div':
            return
        for block in self.active:
            block['depth'] += 1
        attributes = dict(attrs)
        if self.predicate(attributes):
            self.active.append({
                'attributes': attributes,
                'content_start': self._offset() + len(self.get_starttag_text() or ''),
                'depth': 1,
            })

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == 'div':
            attributes = dict(attrs)
            if self.predicate(attributes):
                self.blocks.append((attributes, ''))

    def handle_endtag(self, tag):
        if tag.lower() != 'div':
            return
        end = self._offset()
        finished = []
        for block in self.active:
            block['depth'] -= 1
            if block['depth'] == 0:
                finished.append(block)
        self.active = [block for block in self.active if block['depth'] > 0]
        self.blocks.extend(
            (block['attributes'], self.source[block['content_start']:end])
            for block in finished
        )


def _product_divs(source, predicate):
    parser = _ProductDivParser(source, predicate)
    parser.feed(source)
    parser.close()
    if parser.active:
        raise ValueError('Product card element did not close')
    return parser.blocks


def parse_products(source):
    products = {}
    cards = _product_divs(
        source,
        lambda attrs: 'product-grid-item' in attrs.get('class', '').split(),
    )
    for attrs, block in cards:
        product_id = attrs.get('data-id', '')
        if not product_id.isdigit():
            raise ValueError('Product card missing numeric data-id')
        title=re.search(r'<h[23]\b[^>]*class="[^"]*wd-entities-title[^"]*"[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',block,re.S)
        if not title:
            raise ValueError('Product card title schema changed')
        authors=re.findall(r'<a\b[^>]*href="[^"]*/book-author/[^"]*"[^>]*>(.*?)</a>',block,re.S)
        classes=attrs.get('class', '').split()
        price=re.search(r'<span class="woocommerce-Price-amount amount">(.*?)</bdi>',block,re.S)
        p={'id':product_id,'title':text_of(title.group(2)),'authors':sorted(set(text_of(a) for a in authors)),'url':html.unescape(title.group(1)),'stock':'in_stock' if 'instock' in classes else 'out_of_stock' if 'outofstock' in classes else 'unknown','price':text_of(price.group(1)) if price else None}
        old=products.get(p['id'])
        if old and (old['title'],old['stock'])!=(p['title'],p['stock']):
            raise ValueError('Conflicting duplicate product cards')
        products[p['id']]=p
    return list(products.values())

def search_books(query,mode='title',max_pages=30):
    if not query.strip() or mode not in ('title','author'):
        raise ValueError('Nonempty query and title/author mode required')
    first=BASE+'?'+urlencode({'s':query,'post_type':'product','dgwt_wcas':'1'})
    queue,visited,products=[first],set(),{}
    while queue:
        url=queue.pop(0)
        if url in visited:
            continue
        if len(visited)>=max_pages:
            raise ValueError('Pagination limit exceeded; results are incomplete')
        source=fetch(url)
        visited.add(url)
        main_divs = _product_divs(
            source,
            lambda attrs: bool(re.fullmatch(r'product-\d+', attrs.get('id', '')))
            and 'product' in attrs.get('class', '').split(),
        )
        main = main_divs[0] if main_divs else None
        if main:
            main_attrs, body = main
            main_id = re.fullmatch(r'product-(\d+)', main_attrs.get('id', ''))
            if main_id is None:
                raise ValueError('Product page has an invalid product id')
            product_id = main_id.group(1)
            title=re.search(r'<h1[^>]*>(.*?)</h1>',body,re.S)
            canonical=re.search(r'<link rel="canonical" href="([^"]+)"',source)
            if not title or not canonical:
                raise ValueError('Unrecognized redirected product page')
            classes=main_attrs.get('class', '').split()
            authors=re.findall(r'<a\b[^>]*href="[^"]*/book-author/[^"]*"[^>]*>(.*?)</a>',body,re.S)
            price=re.search(r'<span class="woocommerce-Price-amount amount">(.*?)</bdi>',body,re.S)
            cards=[{'id':product_id,'title':text_of(title.group(1)),'authors':sorted(set(text_of(a) for a in authors)),'url':html.unescape(canonical.group(1)),'stock':'in_stock' if 'instock' in classes else 'out_of_stock' if 'outofstock' in classes else 'unknown','price':text_of(price.group(1)) if price else None}]
        else:
            if 'תוצאות חיפוש עבור' not in source:
                raise ValueError('Unexpected search page; do not interpret as no results')
            cards=parse_products(source)
        if not cards and not any(t in source for t in ('לא נמצאו','No products were found','לא נמצא')):
            raise ValueError('No cards and no explicit empty-results marker')
        for p in cards:
            old=products.get(p['id'])
            if old and old['stock']!=p['stock']:
                raise ValueError('Stock changed between pages; retry')
            products[p['id']]=p
        if not main:
            for attrs in re.findall(r'<a\b([^>]+)>',source):
                if re.search(r'class="[^"]*page-numbers',attrs):
                    href=re.search(r'href="([^"]+)"',attrs)
                    if href:
                        link=urljoin(url,html.unescape(href.group(1)))
                        if link not in visited and link not in queue:
                            queue.append(link)
    results=list(products.values())
    for p in results:
        p['exact_match']=normalize(query)==normalize(p['title']) if mode=='title' else any(normalize(query)==normalize(a) for a in p['authors'])
    results.sort(key=lambda p:(not p['exact_match'],p['title'],p['id']))
    return {'query':query,'mode':mode,'search_url':first,'checked_at':datetime.now(timezone.utc).isoformat(),'pages':len(visited),'total':len(results),'products':results}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('query')
    parser.add_argument('--mode',choices=['title','author'],default='title')
    args=parser.parse_args()
    print(json.dumps(search_books(args.query,args.mode),ensure_ascii=False,indent=2))
