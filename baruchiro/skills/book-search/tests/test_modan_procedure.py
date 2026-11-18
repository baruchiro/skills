"""Offline documentation contracts, not live browser or stock tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModanProcedureTests(unittest.TestCase):
    def setUp(self):
        self.guide = (ROOT / 'references/modan.md').read_text(encoding='utf-8')

    def test_guide_is_discoverable_and_provider_is_named(self):
        self.assertIn('references/modan.md', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('references/modan.md', (ROOT / 'README.md').read_text(encoding='utf-8'))
        providers = (ROOT / 'references/providers.md').read_text(encoding='utf-8')
        self.assertIn('https://www.modan.co.il/', providers)
        self.assertIn('(modan.md)', providers)

    def test_search_checks_title_author_empty_and_incomplete_results(self):
        for phrase in ('full requested title', 'author separately', 'bskeyword=',
                       'explicit empty result', 'not zero results', 'pagination',
                       'incomplete coverage', 'Do not invent legacy search endpoints'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)

    def test_price_is_rendered_main_product_not_stock_or_checkout_total(self):
        for phrase in ('main product', 'finish rendering', 'crossed-out original price',
                       'not a checkout total', 'availability unknown',
                       'not confirmed physical stock', 'recommendations'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)

    def test_manual_validation_and_limits_are_explicit(self):
        for phrase in ('2026-11-18', 'not an executable adapter',
                       'No Modan scraper or automated browser test',
                       'pagination behavior', 'outside this package',
                       'Do not add to cart', 'unattended monitoring'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)


if __name__ == '__main__':
    unittest.main()
