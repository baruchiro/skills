from pathlib import Path
import unittest
P = Path(__file__).resolve().parents[1]
class AccessProcedureTests(unittest.TestCase):
    def test_route_and_safety_distinctions(self):
        text = (P/'references/library-subscription.md').read_text()
        for token in ['telaviv.overdrive.com', 'storytel.com/il', 'Signed-out', 'zero licensed copies', 'personal access', 'Hebrew', 'Never click Borrow', 'trial/signup']:
            self.assertIn(token, text)
    def test_discoverable(self):
        for name in ['SKILL.md', 'README.md', 'references/providers.md']:
            self.assertIn('library-subscription.md', (P/name).read_text())
