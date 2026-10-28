#!/usr/bin/env python3
"""Focused CLI smoke check; synthetic inputs, no full suite run."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def main():
    regression_tree = ast.parse((PACKAGE / 'tests/test_voucher_lookup.py').read_text())
    count = sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
                for node in regression_tree.body)
    assert count == 19, count
    print(f'Regression inventory: {count} functions (not executed by smoke)')
    with tempfile.TemporaryDirectory(prefix='voucher-smoke-') as folder:
        target = Path(folder)
        for fixture in (PACKAGE / 'examples').glob('*.json'):
            shutil.copyfile(fixture, target / fixture.name)
        base = [sys.executable, str(PACKAGE / 'scripts/voucher_lookup.py')]
        config = ['--config', str(target / 'config.json')]
        validated = subprocess.run(base + ['validate'] + config,
                                   capture_output=True, text=True, check=True)
        assert 'OK' in validated.stdout
        print('validate: exit 0, inputs valid')
        lookup = subprocess.run(base + ['lookup'] + config + [
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json'],
            capture_output=True, text=True, check=True)
        result = json.loads(lookup.stdout)
        assert result['status'] == 'ok'
        assert result['data_kind'] == 'synthetic'
        assert result['merchant']['id'] == 'kravitz'
        assert len(result['holdings']) == 5
        assert len({h['holding_id'] for h in result['holdings']}) == 5
        assert all(h['balance'] is None for h in result['holdings'])
        print('lookup: exit 0, status ok, synthetic, 5 unique holdings, amounts hidden')
    print('Focused CLI smoke: PASS')


if __name__ == '__main__':
    main()
