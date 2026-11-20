#!/usr/bin/env python3
"""Small, read-only public catalog searches. Python standard library only.

No cookies, credentials, playback, loans or account mutations. Public records
are candidates, never proof of personal library/subscription entitlement.
"""
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
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
