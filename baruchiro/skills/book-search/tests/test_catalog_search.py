"""Synthetic offline fixtures, no copied catalog data or private queries."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'scripts'))
import _catalog_common as c
import overdrive_search as od
import storytel_search as st

def search(provider, *args, **kwargs):
    return {'overdrive': od.search, 'storytel': st.search}[provider](*args, **kwargs)


def od_row(id='123', available=1, owned=2):
    return {'id': id, 'title': 'Synthetic Book',
            'creators': [{'name': 'Example Author', 'role': 'Author'}, {'name': 'Example Reader', 'role': 'Narrator'}],
            'languages': [{'id': 'he'}], 'type': {'id': 'audiobook'},
            'formats': [{'id': 'audiobook-overdrive', 'isbn': 'synthetic'}],
            'availableCopies': available, 'ownedCopies': owned, 'isHoldable': True}


def od_page(rows, total=None):
    total = len(rows) if total is None else total
    text = f'Showing 1-{len(rows)} of {total} results' if total else "We couldn't find any matches"
    return ('window.OverDrive.titleCollection = ' + json.dumps(rows) + ';<h1>' + text + '</h1>'
            + 'window.OverDrive.mediaItems = {"999":{"title":"Unrelated recommendation"}};')


def st_row(id='123'):
    return {'resultType': 'book', 'id': id, 'title': 'Synthetic Book',
            'authors': [{'name': 'Example Author'}], 'narrators': [], 'language': 'en',
            'shareUrl': f'https://www.storytel.com/il/books/synthetic-book-{id}',
            'formats': [{'id': '456', 'type': 'abook', 'isReleased': True,
                         'availabilityInfo': [{'type': 'subscription', 'isReleased': True}]}]}


def st_page(rows, total=None, token=None):
    return json.dumps({'items': rows, 'totalCount': len(rows) if total is None else total,
                       'nextPageToken': token})


class SequenceReader:
    def __init__(self, *pages):
        self.pages = list(pages)
        self.urls = []
    def get(self, url):
        self.urls.append(url)
        value = self.pages.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class ParserTests(unittest.TestCase):
    def test_overdrive_main_collection_not_recommendations(self):
        rows, total = od.parse_overdrive(od_page([od_row()]))
        self.assertEqual(total, 1)
        self.assertEqual([r['id'] for r in rows], ['123'])
        self.assertEqual(rows[0]['authors'], ['Example Author'])
        self.assertEqual(rows[0]['contributors'][1]['role'], 'Narrator')
        self.assertEqual(rows[0]['languages'], ['he'])
        self.assertEqual(rows[0]['personal_entitlement'], 'unverified')

    def test_overdrive_copies_hold_and_zero_license_are_separate(self):
        for available, owned, expected in [(1, 2, 'available'), (0, 2, 'hold'), (0, 0, 'no_licensed_copies')]:
            with self.subTest(expected=expected):
                rows, _ = od.parse_overdrive(od_page([od_row(available=available, owned=owned)]))
                self.assertEqual(rows[0]['public_availability'], expected)

    def test_empty_requires_both_explicit_marker_and_empty_collection(self):
        self.assertEqual(od.parse_overdrive(od_page([])), ([], 0))
        for source in ['Access denied', 'window.OverDrive.titleCollection = [];',
                       'window.OverDrive.titleCollection = {}; We could not find any matches',
                       'window.OverDrive.titleCollection = not-json;']:
            with self.subTest(source=source), self.assertRaises(c.CatalogError):
                od.parse_overdrive(source)

    def test_overdrive_missing_identity_and_inconsistent_counts_fail(self):
        for key, value in [('id', 'not-an-id'), ('creators', None), ('availableCopies', None),
                           ('availableCopies', 5), ('ownedCopies', -1)]:
            row = od_row(); row[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(c.CatalogError):
                od.parse_overdrive(od_page([row]))

    def test_storytel_normalization_keeps_language_formats_and_entitlement(self):
        rows, total, token = st.parse_storytel(json.loads(st_page([st_row()])))
        self.assertEqual((total, token), (1, None))
        self.assertEqual(rows[0]['languages'], ['en'])
        self.assertEqual(rows[0]['formats'][0]['catalog_access'][0]['type'], 'subscription')
        self.assertEqual(rows[0]['personal_entitlement'], 'unverified')

    def test_storytel_invalid_response_is_not_zero_results(self):
        for data in [{}, {'items': [], 'totalCount': -1}, {'items': []},
                     {'items': [dict(st_row(), resultType='tag')], 'totalCount': 1},
                     {'items': [dict(st_row(), shareUrl='https://www.storytel.com/us/books/synthetic-123')], 'totalCount': 1}]:
            with self.subTest(data=data), self.assertRaises(c.CatalogError):
                st.parse_storytel(data)

    def test_exact_match_does_not_conflate_subtitle_or_author(self):
        row = {'title': 'Synthetic: Book', 'authors': ['Example Author']}
        self.assertTrue(c.exact_candidate(row, 'synthetic book', 'title'))
        self.assertFalse(c.exact_candidate(row, 'Synthetic Book 2', 'title'))
        self.assertTrue(c.exact_candidate(row, 'Example Author', 'author'))
        self.assertFalse(c.exact_candidate(row, 'Synthetic Book', 'author'))


class SearchTests(unittest.TestCase):
    def test_overdrive_author_url_and_query_encoding(self):
        reader = SequenceReader(od_page([od_row()]))
        result = search('overdrive', 'A & B', 'author', reader=reader)
        self.assertTrue(result['complete'])
        self.assertIn('creator=A+%26+B', reader.urls[0])
        self.assertNotIn('page=', reader.urls[0])

    def test_overdrive_pagination_limit_is_explicit_not_absence(self):
        reader = SequenceReader(od_page([od_row()], total=50))
        result = search('overdrive', 'Book', reader=reader)
        self.assertFalse(result['complete'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(len(reader.urls), 1)
        self.assertIn('robots.txt', result['errors'][0])

    def test_storytel_opaque_pagination_and_dedup(self):
        reader = SequenceReader(st_page([st_row('1')], 2, 'opaque/+='), st_page([st_row('1'), st_row('2')], 2))
        result = search('storytel', 'Book', reader=reader)
        self.assertTrue(result['complete'])
        self.assertEqual(result['count'], 2)
        self.assertIn('page=opaque%2F%2B%3D', reader.urls[1])
        self.assertIn('searchFor=books', reader.urls[0])
        self.assertIn('store=STHP-IL', reader.urls[0])

    def test_storytel_partial_results_survive_network_failure(self):
        reader = SequenceReader(st_page([st_row()], 2, 'next'), HTTPError(ST_URL, 429, 'rate limited', {}, None))
        result = search('storytel', 'Book', reader=reader)
        self.assertFalse(result['complete'])
        self.assertEqual(result['count'], 1)
        self.assertIn('429', result['errors'][0])
        self.assertEqual(len(reader.urls), 2)  # No retries.

    def test_storytel_count_mismatch_and_repeated_token(self):
        for pages in [(st_page([st_row()], 2),),
                      (st_page([st_row()], 2, 'a'), st_page([st_row('2')], 2, 'a')),
                      (st_page([st_row()], 2, 'a'), st_page([st_row('2')], 3))]:
            result = search('storytel', 'Book', reader=SequenceReader(*pages))
            self.assertFalse(result['complete'])
            self.assertTrue(result['errors'])
            self.assertGreaterEqual(result['count'], 1)

    def test_storytel_page_bound_and_zero_results(self):
        result = search('storytel', 'Book', max_pages=1, reader=SequenceReader(st_page([st_row()], 2, 'next')))
        self.assertFalse(result['complete'])
        result = search('storytel', 'No title', reader=SequenceReader(st_page([])))
        self.assertTrue(result['complete']); self.assertEqual(result['count'], 0)

    def test_robots_denial_does_not_become_no_results(self):
        reader = SequenceReader(c.CatalogError('robots denied'))
        result = search('overdrive', 'Book', reader=reader)
        self.assertFalse(result['complete'])
        self.assertNotIn('total', result)
        self.assertTrue(result['errors'])
        self.assertIn('attempted_url', result)

    def test_bad_inputs(self):
        for provider, query, mode, limit in [('storytel', '', 'title', 1),
                                            ('storytel', 'x', 'title', 50), ('overdrive', 'x', 'other', 1)]:
            with self.assertRaises(ValueError): search(provider, query, mode, limit)


ST_URL = 'https://api.storytel.net/search/client/web'


class Response(io.BytesIO):
    def __init__(self, body, url):
        super().__init__(body.encode()); self.url = url
    def geturl(self): return self.url


class FakeOpener:
    def __init__(self, robots='User-agent: *\nAllow: /', error=None):
        self.calls = []; self.robots = robots; self.error = error
    def open(self, req, timeout):
        self.calls.append(req)
        if req.full_url.endswith('/robots.txt'):
            if self.robots is None: raise HTTPError(req.full_url, 404, 'not found', {}, None)
            return Response(self.robots, req.full_url)
        if self.error: raise self.error
        return Response('payload', req.full_url)


class NetworkSafetyTests(unittest.TestCase):
    def test_disallowed_path_and_redirect_host(self):
        for url in ['http://api.storytel.net/search/client/web', 'https://evil.invalid/search',
                    'https://api.storytel.net/account', 'https://telaviv.overdrive.com/search?page=2',
                    'https://telaviv.overdrive.com/account/loans',
                    'https://user:secret@telaviv.overdrive.com/search']:
            with self.subTest(url=url), self.assertRaises(c.CatalogError): c.safe_url(url)
        redirect = c.SafeRedirect()
        with self.assertRaises(c.CatalogError):
            redirect.redirect_request(type('Req', (), {'full_url': ST_URL})(), None, 302, '', {}, 'https://telaviv.overdrive.com/search')

    def test_robots_denial_prevents_search(self):
        opener = FakeOpener('User-agent: *\nDisallow: /search')
        reader = c.PublicReader(opener, clock=lambda: 100, sleep=lambda _: None)
        with self.assertRaises(c.CatalogError): reader.get(ST_URL)
        self.assertEqual(len(opener.calls), 1)

    def test_robot_404_is_not_denial_and_delay_is_applied(self):
        opener = FakeOpener(robots=None); delays=[]
        reader = c.PublicReader(opener, clock=lambda: 100, sleep=delays.append)
        self.assertEqual(reader.get(ST_URL), 'payload')
        self.assertEqual(delays, [2])
        for req in opener.calls:
            self.assertNotIn('Cookie', req.headers)
            self.assertEqual(req.get_method(), 'GET')

    def test_denial_no_retries(self):
        opener = FakeOpener(error=HTTPError(ST_URL, 403, 'denied', {}, None))
        reader = c.PublicReader(opener, clock=lambda: 100, sleep=lambda _: None)
        with self.assertRaises(HTTPError): reader.get(ST_URL)
        self.assertEqual(len(opener.calls), 2)  # robots + one search


if __name__ == '__main__':
    unittest.main()
