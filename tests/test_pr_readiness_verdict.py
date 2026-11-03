"""Offline package checks; optional integration with an unmodified Hermes checkout.

Run: python3 -m unittest discover -s tests -v
Guard integration: HERMES_AGENT_ROOT=/path/to/hermes-agent <same command>
These tests live outside the installable skill bundle, not behind scan exclusions.
"""
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

BUNDLE = Path(__file__).resolve().parents[1] / 'baruchiro/skills/pr-readiness-verdict'


class EvaluationPackageTests(unittest.TestCase):
    def test_evaluation_scenarios_have_readable_fixtures_and_expectations(self):
        data = json.loads((BUNDLE / 'evals/evals.json').read_text())
        self.assertEqual(data['skill_name'], BUNDLE.name)
        self.assertEqual([case['name'] for case in data['evals']], [
            'breaking-rename-and-unsafe-feature', 'hygiene-violations',
            'safe-additive-optional-field',
        ])
        for case in data['evals']:
            with self.subTest(scenario=case['name']):
                self.assertTrue(case['prompt'].strip())
                self.assertTrue(case['expected_output'].strip())
                self.assertTrue(case['expectations'])
                self.assertTrue(case['files'])
                for filename in case['files']:
                    fixture = (BUNDLE / filename).resolve()
                    self.assertTrue(fixture.is_relative_to(BUNDLE.resolve()))
                    self.assertTrue(fixture.read_text().startswith('diff --git '))

    def test_hygiene_case_still_requires_path_confinement_and_symlink_review(self):
        cases = json.loads((BUNDLE / 'evals/evals.json').read_text())['evals']
        case = next(case for case in cases if case['name'] == 'hygiene-violations')
        for requirement in ('relativePath', 'path.resolve', 'EXPORT_ROOT',
                            'symlinks', 'parent-directory segments',
                            'outside the intended export directory'):
            self.assertIn(requirement, case['expected_output'])
        self.assertTrue(any('path traversal risk' in item and 'symlink' in item
                            for item in case['expectations']))
        fixture = (BUNDLE / case['files'][0]).read_text()
        self.assertIn('path.resolve(EXPORT_ROOT, relativePath)', fixture)
        self.assertIn('return readFileSync(targetPath)', fixture)


@unittest.skipUnless(os.environ.get('HERMES_AGENT_ROOT'),
                     'Set HERMES_AGENT_ROOT to exercise the real Hermes guard')
class HermesGuardIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(os.environ['HERMES_AGENT_ROOT']).resolve()
        if not (root / 'tools/skills_guard.py').is_file():
            raise RuntimeError('HERMES_AGENT_ROOT must name a Hermes source checkout')
        sys.path.insert(0, str(root))
        cls.guard = importlib.import_module('tools.skills_guard')
        print(f'Guard: {cls.guard.SCANNER_VERSION} ({cls.guard.__file__})')

    def test_entire_community_bundle_is_allowed_without_force(self):
        result = self.guard.scan_skill(BUNDLE, source='community')
        allowed, reason = self.guard.should_allow_install(result, force=False)
        self.assertEqual(result.trust_level, 'community')
        self.assertIs(allowed, True, reason)
        self.assertFalse(any(f.severity in ('critical', 'high', 'medium')
                             for f in result.findings), result.findings)
        print(f'Current bundle: {result.verdict}; {reason}')

    def test_original_evaluation_example_remains_hard_blocked(self):
        # Recreate the original inert example in a temporary copy; never read
        # any external file or execute the deliberately vulnerable fixture.
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / BUNDLE.name
            shutil.copytree(BUNDLE, bundle)
            eval_path = bundle / 'evals/evals.json'
            data = json.loads(eval_path.read_text())
            data['evals'][1]['expected_output'] += " Example: '../../etc/passwd'."
            eval_path.write_text(json.dumps(data, indent=2))
            result = self.guard.scan_skill(bundle, source='community')
            self.assertEqual(result.verdict, 'dangerous')
            self.assertTrue({'path_traversal', 'system_passwd_access'} <=
                            {f.pattern_id for f in result.findings})
            for force in (False, True):
                allowed, reason = self.guard.should_allow_install(result, force=force)
                self.assertIs(allowed, False, reason)
            print('Original example: dangerous; hard-blocked with and without force')


if __name__ == '__main__':
    unittest.main()
