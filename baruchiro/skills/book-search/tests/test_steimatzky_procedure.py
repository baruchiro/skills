"""Offline documentation contracts, not live browser or stock tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SteimatzkyProcedureTests(unittest.TestCase):
    def setUp(self):
        self.guide = (ROOT / 'references/steimatzky.md').read_text(encoding='utf-8')

    def test_guide_is_discoverable_and_provider_is_named(self):
        self.assertIn('references/steimatzky.md', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('references/steimatzky.md', (ROOT / 'README.md').read_text(encoding='utf-8'))
        providers = (ROOT / 'references/providers.md').read_text(encoding='utf-8')
        self.assertIn('https://www.steimatzky.co.il/', providers)
        self.assertIn('(steimatzky.md)', providers)

    def test_search_checks_title_author_empty_and_incomplete_results(self):
        for phrase in ('full requested title', 'author separately', 'catalogsearch/result',
                       'לא נמצאו תוצאות לחיפוש שלך', 'not zero results',
                       'finish rendering', 'incomplete coverage',
                       'Do not invent legacy search endpoints'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)

    def test_price_format_and_availability_are_kept_separate(self):
        for phrase in ('main product', 'מחיר מוצר', 'המחיר הקטלוגי של הפריט',
                       'מודפס', 'דיגיטלי', 'not a checkout total',
                       'availability unknown', 'not confirmed physical stock',
                       'not valid in branches', 'recommendations'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)

    def test_manual_validation_and_limits_are_explicit(self):
        for phrase in ('2026-11-19', 'not an executable adapter',
                       'No Steimatzky scraper or automated browser test',
                       'pagination behavior', 'outside this package',
                       'Do not add to cart', 'unattended monitoring',
                       'non-book merchandise'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)


if __name__ == '__main__':
    unittest.main()
