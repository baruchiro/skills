import unittest
from io import BytesIO
from unittest.mock import patch
import rebooks_search as r

def card(id='1',stock='instock',author='קמילה ריד'):
    return f'<div class="product-grid-item product {stock}" data-id="{id}"><h3 class="wd-entities-title"><a href="https://rebooks.org.il/product/book/">ספר</a></h3><a href="https://rebooks.org.il/book-author/a/">{author}</a></div>'
PAGE='תוצאות חיפוש עבור '+card()

class Tests(unittest.TestCase):
    def test_duplicates(self):
        self.assertEqual(len(r.parse_products(card()+card())),1)
    def test_stock(self):
        self.assertEqual(r.parse_products(card(stock='outofstock'))[0]['stock'],'out_of_stock')
    def test_unknown_stock(self):
        self.assertEqual(r.parse_products(card(stock=''))[0]['stock'],'unknown')
    def test_author_not_false_match(self):
        with patch.object(r,'fetch',return_value=PAGE):
            self.assertFalse(r.search_books('אחר','author')['products'][0]['exact_match'])
    def test_author_match(self):
        with patch.object(r,'fetch',return_value=PAGE):
            self.assertTrue(r.search_books('קמילה ריד','author')['products'][0]['exact_match'])
    def test_pagination(self):
        more='<a class="page-numbers" href="https://rebooks.org.il/page/2/?s=x">2</a>'
        with patch.object(r,'fetch',side_effect=[PAGE+more,PAGE]):
            result=r.search_books('ספר')
        self.assertEqual((result['pages'],result['total']),(2,1))
    def test_redirect_ignores_recommendations(self):
        source='<link rel="canonical" href="https://rebooks.org.il/product/main/"><div id="product-42" class="product outofstock"><h1>ספר</h1>'+card()
        with patch.object(r,'fetch',return_value=source):
            result=r.search_books('ספר')
        self.assertEqual(result['total'],1)
        self.assertEqual(result['products'][0]['id'],'42')
        self.assertEqual(result['products'][0]['stock'],'out_of_stock')
    def test_unicode_url(self):
        with patch.object(r,'urlopen',return_value=BytesIO(b'page')) as opener:
            self.assertEqual(r.fetch('https://rebooks.org.il/product/ספר/'),'page')
        self.assertTrue(opener.call_args.args[0].full_url.isascii())
    def test_foreign_host(self):
        with self.assertRaises(ValueError):r.fetch('https://example.com/')
    def test_blocked_is_error(self):
        with patch.object(r,'fetch',return_value='Access denied'):
            with self.assertRaises(ValueError):r.search_books('ספר')
    def test_explicit_empty(self):
        with patch.object(r,'fetch',return_value='תוצאות חיפוש עבור לא נמצאו'):
            self.assertEqual(r.search_books('ספר')['total'],0)
    def test_missing_cards_is_error(self):
        with patch.object(r,'fetch',return_value='תוצאות חיפוש עבור'):
            with self.assertRaises(ValueError):r.search_books('ספר')
    def test_typo_not_normalized(self):
        self.assertNotEqual(r.normalize('הנעלים'),r.normalize('הנעליים'))
    def test_punctuation_normalized(self):
        self.assertEqual(r.normalize('היי־טק'),r.normalize('היי-טק'))
    def test_conflicting_stock_is_error(self):
        with self.assertRaises(ValueError):r.parse_products(card()+card(stock='outofstock'))
    def test_limit_is_error(self):
        with patch.object(r,'fetch',return_value=PAGE+'<a class="page-numbers" href="https://rebooks.org.il/page/2/">2</a>'):
            with self.assertRaises(ValueError):r.search_books('ספר',max_pages=1)

if __name__=='__main__':unittest.main()
