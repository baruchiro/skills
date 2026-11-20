"""Uniform source entry points and honest capability handoff, offline only."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import _search_common as common


class SourceStructureTests(unittest.TestCase):
    def test_every_target_has_matching_reference_and_script(self):
        registry = common.sources()
        self.assertEqual(set(registry), {'rebooks','evrit','steimatzky','tzomet','overdrive','storytel'})
        index = (ROOT/'references/providers.md').read_text(encoding='utf-8')
        for source, item in registry.items():
            self.assertEqual(item['script'], f'scripts/{source}_search.py')
            self.assertEqual(item['reference'], f'references/{source}.md')
            self.assertTrue((ROOT/item['script']).is_file())
            text = (ROOT/item['reference']).read_text(encoding='utf-8')
            self.assertIn(f'{source}_search.py', text)
            self.assertIn(item['entry_url'], text)
            self.assertIn(f'{source}.md', index)
            self.assertIn(f'{source}_search.py', index)

    def test_all_entry_points_accept_same_help_flags_without_network(self):
        for source, item in common.sources().items():
            with self.subTest(source=source):
                proc = subprocess.run([sys.executable,str(ROOT/item['script']),'--help'],capture_output=True,text=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                for flag in ['--mode','--max-pages','--output']:
                    self.assertIn(flag,proc.stdout)

    def test_manual_sources_are_explicit_incomplete_no_network_and_not_absence(self):
        for source in ['evrit','steimatzky','tzomet']:
            module = importlib.import_module(source+'_search')
            with patch('urllib.request.urlopen', side_effect=AssertionError('no network')):
                for mode in ['title','author']:
                    result = module.search('Synthetic query',mode)
                    self.assertEqual(result['status'],'manual_required')
                    self.assertFalse(result['complete'])
                    self.assertEqual(result['products'],[])
                    self.assertTrue(result['errors'])
                    self.assertNotIn('total', result)
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code=common.run_cli(source,module.search,['Synthetic query','--mode',mode])
                    self.assertEqual(code,2)
                    self.assertEqual(json.loads(out.getvalue())['status'],'manual_required')

    def test_common_envelope_on_all_source_success_or_failure(self):
        required={'provider','query','mode','checked_at','capability','reference','entry_url','status','complete','products','count','errors'}
        for source in common.sources():
            for complete in [True,False]:
                def fake(*args):
                    return {'complete':complete,'products':[],'count':0,'errors':[] if complete else ['synthetic failure']}
                out=io.StringIO()
                with contextlib.redirect_stdout(out):
                    code=common.run_cli(source,fake,['Synthetic query'])
                result=json.loads(out.getvalue())
                self.assertLessEqual(required,set(result))
                self.assertEqual(code,0 if complete else 2)
                self.assertEqual(result['status'],'complete' if complete else 'incomplete')

    def test_network_exception_returns_incomplete_json(self):
        def fail(*args): raise OSError('synthetic network failure')
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=common.run_cli('rebooks',fail,['Synthetic query'])
        result=json.loads(out.getvalue())
        self.assertEqual(code,2)
        self.assertFalse(result['complete'])
        self.assertIn('OSError',result['errors'][0])

    def test_output_saved_outside_package_only(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output.json'
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                common.run_cli('evrit',lambda *a: common.manual_result('evrit','Synthetic','title'),['Synthetic','--output',str(output)])
            self.assertEqual(output.read_text(encoding='utf-8'),out.getvalue())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            common.run_cli('evrit',lambda *a: {},['Synthetic','--output',str(ROOT/'private-query.json')])
        self.assertFalse((ROOT/'private-query.json').exists())

    def test_rebooks_python_api_preserved_and_cli_cap_is_passed(self):
        import rebooks_search as r
        data={'query':'Synthetic','mode':'title','search_url':'https://rebooks.org.il/','pages':1,'total':0,'products':[]}
        with patch.object(r,'search_books',return_value=data) as search:
            result=r.search('Synthetic',max_pages=2)
            search.assert_called_once_with('Synthetic','title',2)
        self.assertTrue(result['complete'])
        self.assertEqual(result['count'],0)
        with patch.object(r,'search_books',side_effect=OSError('denied')):
            self.assertFalse(r.search('Synthetic')['complete'])

    def test_legacy_evrit_verifier_preserved(self):
        import evrit_search as e
        import evrit_verify as old
        self.assertIs(e.parse_product_page,old.parse_product_page)
        self.assertIs(e.search_via_ddg,old.search_via_ddg)
        self.assertIs(e.parse_author_page,old.parse_author_page)

    def test_old_mixed_catalog_interface_removed(self):
        self.assertFalse((ROOT/'scripts/catalog_search.py').exists())
        self.assertFalse((ROOT/'references/library-subscription.md').exists())


if __name__=='__main__': unittest.main()
