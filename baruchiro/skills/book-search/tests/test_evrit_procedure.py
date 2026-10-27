"""Documentation contract for the manual e-vrit provider (no scraper claim)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EvritProcedureTests(unittest.TestCase):
    def test_provider_guide_is_discoverable_from_skill(self):
        self.assertIn('references/evrit.md', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))

    def test_guide_distinguishes_library_label_from_digital_format(self):
        guide = ROOT / 'references/evrit.md'
        self.assertTrue(guide.is_file(), 'Missing e-vrit search and eligibility procedure')
        text = guide.read_text(encoding='utf-8')
        self.assertIn('ספריה ציבורית דיגיטלית', text)
        self.assertIn('not equivalent', text)
        self.assertIn('unknown', text)
        self.assertIn('recommendation', text)


if __name__ == '__main__':
    unittest.main()
