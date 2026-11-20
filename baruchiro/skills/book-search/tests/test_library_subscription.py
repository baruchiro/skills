from pathlib import Path
import unittest
P = Path(__file__).resolve().parents[1]
class AccessProcedureTests(unittest.TestCase):
    def test_source_specific_limits(self):
        od = (P/'references/overdrive.md').read_text(encoding='utf-8')
        st = (P/'references/storytel.md').read_text(encoding='utf-8')
        for token in ['telaviv.overdrive.com', 'Signed-out', 'zero licensed copies', 'Hebrew', 'Never click Borrow']:
            self.assertIn(token, od)
        for token in ['storytel.com/il', 'personal access', 'Trial/signup', 'nextPageToken', 'Never click Borrow']:
            self.assertIn(token, st)
    def test_discoverable(self):
        for name in ['SKILL.md', 'README.md']:
            self.assertIn('references/providers.md', (P/name).read_text(encoding='utf-8'))
        central = (P/'references/providers.md').read_text(encoding='utf-8')
        for provider in ['overdrive', 'storytel']:
            self.assertIn(provider+'.md', central)
            self.assertIn(provider+'_search.py', central)
