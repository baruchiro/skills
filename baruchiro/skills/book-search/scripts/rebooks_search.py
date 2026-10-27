"""Deterministic, read-only Rebooks search; Python standard library only."""
import argparse
import html
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin, urlparse, quote
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
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1+attempt)

def parse_products(source):
    starts = list(re.finditer(r'<div\b[^>]*class="([^"]*product-grid-item[^"]*)"[^>]*data-id="(\d+)"[^>]*>',source))
    products = {}
    for i,m in enumerate(starts):
        block=source[m.end():starts[i+1].start() if i+1<len(starts) else len(source)]
        title=re.search(r'<h[23]\b[^>]*class="[^"]*wd-entities-title[^"]*"[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',block,re.S)
        if not title:
            raise ValueError('Product card title schema changed')
        authors=re.findall(r'<a\b[^>]*href="[^"]*/book-author/[^"]*"[^>]*>(.*?)</a>',block,re.S)
        classes=m.group(1).split()
        price=re.search(r'<span class="woocommerce-Price-amount amount">(.*?)</bdi>',block,re.S)
        p={'id':m.group(2),'title':text_of(title.group(2)),'authors':sorted(set(text_of(a) for a in authors)),'url':html.unescape(title.group(1)),'stock':'in_stock' if 'instock' in classes else 'out_of_stock' if 'outofstock' in classes else 'unknown','price':text_of(price.group(1)) if price else None}
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
        main=re.search(r'<div[^>]*id="product-(\d+)"[^>]*class="([^"]+)"',source)
        if main:
            title=re.search(r'<h1[^>]*>(.*?)</h1>',source,re.S)
            canonical=re.search(r'<link rel="canonical" href="([^"]+)"',source)
            if not title or not canonical:
                raise ValueError('Unrecognized redirected product page')
            classes=main.group(2).split()
            end=source.find('product-grid-item',main.end())
            body=source[main.end():end if end>0 else len(source)]
            authors=re.findall(r'<a\b[^>]*href="[^"]*/book-author/[^"]*"[^>]*>(.*?)</a>',body,re.S)
            price=re.search(r'<span class="woocommerce-Price-amount amount">(.*?)</bdi>',body,re.S)
            cards=[{'id':main.group(1),'title':text_of(title.group(1)),'authors':sorted(set(text_of(a) for a in authors)),'url':html.unescape(canonical.group(1)),'stock':'in_stock' if 'instock' in classes else 'out_of_stock' if 'outofstock' in classes else 'unknown','price':text_of(price.group(1)) if price else None}]
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
