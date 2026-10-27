"""Offline checks for distributable package integrity, not agent compliance."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_manifest_covers_exact_shipped_files_with_matching_digests(self):
        manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
        actual = {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in ROOT.rglob('*')
            if p.is_file() and p.name != 'MANIFEST.json'
            and '__pycache__' not in p.parts and p.suffix != '.pyc'
        }
        self.assertEqual(manifest, actual)

    def test_relative_markdown_links_resolve_within_package(self):
        for doc in ROOT.rglob('*.md'):
            for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', doc.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                target = (doc.parent / link.split('#', 1)[0]).resolve()
                with self.subTest(document=str(doc.relative_to(ROOT)), link=link):
                    self.assertTrue(target.is_relative_to(ROOT), 'link escapes package')
                    self.assertTrue(target.is_file(), 'broken relative documentation link')


if __name__ == '__main__':
    unittest.main()
