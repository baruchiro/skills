#!/usr/bin/env python3
"""
Tests for merchant-voucher-lookup.
All tests use synthetic fixtures in a temp directory outside Git.
No network calls.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys

# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
EXAMPLES_DIR = Path(__file__).parent.parent / 'examples'

def run_lookup(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run voucher_lookup.py and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPTS_DIR / 'voucher_lookup.py')] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr

def setup_test_fixture(tmpdir: Path) -> tuple[Path, Path, Path]:
    """Copy synthetic examples to temp dir and return (config, catalog, wallet) paths."""
    config_path = tmpdir / 'config.json'
    catalog_path = tmpdir / 'catalog.json'
    wallet_path = tmpdir / 'wallet.json'
    
    shutil.copy(EXAMPLES_DIR / 'config.json', config_path)
    shutil.copy(EXAMPLES_DIR / 'catalog.json', catalog_path)
    shutil.copy(EXAMPLES_DIR / 'wallet.json', wallet_path)
    
    # Fix paths in config to be relative to temp dir
    config = json.loads(config_path.read_text())
    config['catalog_path'] = 'catalog.json'
    config['wallet_path'] = 'wallet.json'
    config['cache_dir'] = 'cache'
    config_path.write_text(json.dumps(config))
    
    return config_path, catalog_path, wallet_path

def test_validate_success():
    """Validate command succeeds with valid files."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup(['validate', '--config', str(config_path)], cwd=tmpdir)
        assert code == 0, f"Expected 0, got {code}: {err}"
        assert 'OK' in out
        print("✓ test_validate_success")

def test_validate_missing_file():
    """Validate fails with missing catalog."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        (tmpdir / 'catalog.json').unlink()
        code, out, err = run_lookup(['validate', '--config', str(config_path)], cwd=tmpdir)
        assert code == 2, f"Expected 2, got {code}: {err}"
        print("✓ test_validate_missing_file")

def test_lookup_kravitz_physical_supported():
    """Kravitz physical: BUYME ALL supported, BUYME SELECT excluded, תו הזהב unknown."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0, f"Expected 0, got {code}: {err}"
        result = json.loads(out)
        assert result['status'] == 'ok'
        assert result['merchant']['name'] == 'Kravitz'
        
        # Find holdings by holding_id since multiple can have same product_id
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')  # BUYME ALL active
        h2 = next(h for h in result['holdings'] if h['holding_id'] == 'h2')  # BUYME SELECT
        h3 = next(h for h in result['holdings'] if h['holding_id'] == 'h3')  # תו הזהב classic
        h4 = next(h for h in result['holdings'] if h['holding_id'] == 'h4')  # תו הזהב membership
        h5 = next(h for h in result['holdings'] if h['holding_id'] == 'h5')  # BUYME ALL expired
        
        # BUYME ALL (h1) -> supported_candidate
        assert h1['outcome'] == 'supported_candidate', f"h1 outcome: {h1['outcome']}"
        # BUYME SELECT -> excluded (deny rule)
        assert h2['outcome'] == 'excluded', f"h2 outcome: {h2['outcome']}"
        # תו הזהב classic -> unknown (no rule)
        assert h3['outcome'] == 'unknown', f"h3 outcome: {h3['outcome']}"
        # תו הזהב membership -> unknown (no rule)
        assert h4['outcome'] == 'unknown', f"h4 outcome: {h4['outcome']}"
        # Expired (h5) -> unavailable
        assert h5['outcome'] == 'unavailable', f"h5 outcome: {h5['outcome']}"
        print("✓ test_lookup_kravitz_physical_supported")

def test_lookup_kravitz_hebrew_alias():
    """Hebrew alias 'קריביץ' matches Kravitz."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'קריביץ', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0, f"Expected 0, got {code}: {err}"
        result = json.loads(out)
        assert result['status'] == 'ok'
        assert result['merchant']['name'] == 'Kravitz'
        print("✓ test_lookup_kravitz_hebrew_alias")

def test_lookup_merchant_ambiguous():
    """Ambiguous merchant name returns merchant_ambiguous."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        # Add another merchant with same alias
        catalog_path = tmpdir / 'catalog.json'
        catalog = json.loads(catalog_path.read_text())
        catalog['merchants'].append({"id": "kravitz2", "name": "Kravitz 2", "aliases": ["קריביץ"]})
        catalog_path.write_text(json.dumps(catalog))
        
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'קריביץ', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 3, f"Expected 3, got {code}: {err}"
        result = json.loads(out)
        assert result['status'] == 'merchant_ambiguous'
        assert len(result['merchant_candidates']) == 2
        print("✓ test_lookup_merchant_ambiguous")

def test_lookup_merchant_not_found():
    """Unknown merchant returns merchant_not_found."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'UnknownMerchant', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 3, f"Expected 3, got {code}: {err}"
        result = json.loads(out)
        assert result['status'] == 'merchant_not_found'
        print("✓ test_lookup_merchant_not_found")

def test_lookup_fox_home_conditional():
    """FOX Home: תו הזהב classic -> conditional (has condition), membership -> conditional (unverified)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'FOX Home', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0, f"Expected 0, got {code}: {err}"
        result = json.loads(out)
        
        holdings = {h['product_id']: h for h in result['holdings']}
        # Classic card has condition -> conditional
        assert holdings['tav_hazahav_classic_card']['outcome'] == 'conditional'
        assert 'conditions_unresolved' in holdings['tav_hazahav_classic_card']['reason_codes']
        # Membership unverified -> conditional
        assert holdings['tav_hazahav_membership']['outcome'] == 'conditional'
        assert 'evidence_unverified' in holdings['tav_hazahav_membership']['reason_codes']
        print("✓ test_lookup_fox_home_conditional")

def test_lookup_zara_excluded():
    """Zara: BUYME ALL denied -> excluded."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Zara', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0, f"Expected 0, got {code}: {err}"
        result = json.loads(out)
        
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert h1['outcome'] == 'excluded'
        assert 'explicit_exclusion' in h1['reason_codes']
        print("✓ test_lookup_zara_excluded")

def test_lookup_ksp_online_only():
    """KSP: BUYME ALL allowed only online, physical -> unknown."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        
        # Physical channel
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'KSP', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert h1['outcome'] == 'unknown'
        
        # Online channel
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'KSP', '--channel', 'online', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert h1['outcome'] == 'supported_candidate'
        print("✓ test_lookup_ksp_online_only")

def test_lookup_branch_context():
    """Branch ID context affects scope match."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        # Modify rule to have branch_ids
        catalog_path = tmpdir / 'catalog.json'
        catalog = json.loads(catalog_path.read_text())
        for r in catalog['rules']:
            if r['id'] == 'r1':
                r['scope']['branch_ids'] = ['branch-001']
        catalog_path.write_text(json.dumps(catalog))
        
        # Without branch_id -> needs_context
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert h1['outcome'] == 'conditional'
        assert 'context_missing' in h1['reason_codes']
        
        # With matching branch_id -> supported
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--branch-id', 'branch-001', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        h1 = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert h1['outcome'] == 'supported_candidate'
        print("✓ test_lookup_branch_context")

def test_lookup_balance_zero_unavailable():
    """Holding with reported zero balance -> unavailable."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        # Modify wallet to have zero balance active holding
        wallet_path = tmpdir / 'wallet.json'
        wallet = json.loads(wallet_path.read_text())
        wallet['holdings'].append({
            "id": "h6",
            "label": "BUYME ALL - Zero Balance",
            "product_id": "buyme_all_gift",
            "kind": "stored_value",
            "status": "active",
            "expires_on": "2027-12-31",
            "balance": {"amount_minor": 0, "currency": "ILS", "reported_at": "2026-10-01T10:00:00Z", "kind": "user_reported"}
        })
        wallet_path.write_text(json.dumps(wallet))
        
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        zero_holding = next(h for h in result['holdings'] if h['holding_id'] == 'h6')
        assert zero_holding['outcome'] == 'unavailable'
        assert 'reported_zero' in zero_holding['reason_codes']
        print("✓ test_lookup_balance_zero_unavailable")

def test_lookup_balance_unknown():
    """Holding with null balance -> conditional with balance_unknown."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        # Modify wallet to have null balance
        wallet_path = tmpdir / 'wallet.json'
        wallet = json.loads(wallet_path.read_text())
        wallet['holdings'].append({
            "id": "h7",
            "label": "BUYME ALL - Unknown Balance",
            "product_id": "buyme_all_gift",
            "kind": "stored_value",
            "status": "active",
            "expires_on": "2027-12-31",
            "balance": None
        })
        wallet_path.write_text(json.dumps(wallet))
        
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        unk_holding = next(h for h in result['holdings'] if h['holding_id'] == 'h7')
        assert unk_holding['outcome'] == 'conditional'
        assert 'balance_unknown' in unk_holding['reason_codes']
        print("✓ test_lookup_balance_unknown")

def test_lookup_merchant_id():
    """--merchant-id works and is exclusive with --merchant."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant-id', 'kravitz', '--channel', 'physical', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        assert result['merchant']['id'] == 'kravitz'
        print("✓ test_lookup_merchant_id")

def test_lookup_merchant_id_and_name_conflict():
    """--merchant-id and --merchant together -> error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--merchant-id', 'kravitz', '--format', 'json'
        ], cwd=tmpdir)
        assert code == 2, f"Expected 2, got {code}: {err}"
        print("✓ test_lookup_merchant_id_and_name_conflict")

def test_lookup_show_balances():
    """--show-balances includes balance in output."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'json', '--show-balances'
        ], cwd=tmpdir)
        assert code == 0
        result = json.loads(out)
        holding = next(h for h in result['holdings'] if h['holding_id'] == 'h1')
        assert holding['balance'] is not None
        assert holding['balance']['amount_minor'] == 25000
        print("✓ test_lookup_show_balances")

def test_lookup_text_format():
    """Text format produces Hebrew output."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        code, out, err = run_lookup([
            'lookup', '--config', str(config_path),
            '--merchant', 'Kravitz', '--channel', 'physical', '--format', 'text'
        ], cwd=tmpdir)
        assert code == 0
        assert 'רשת:' in out
        assert 'מועמדים נתמכים' in out
        print("✓ test_lookup_text_format")

def test_config_path_outside_git():
    """Config validates paths are outside Git."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        # Create a git repo
        subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
        (tmpdir / '.git').mkdir(exist_ok=True)
        
        config_path = tmpdir / 'config.json'
        catalog_path = tmpdir / 'catalog.json'
        wallet_path = tmpdir / 'wallet.json'
        
        config = {"schema_version": 1, "catalog_path": "catalog.json", "wallet_path": "wallet.json", "cache_dir": "cache", "stale_after_days": 30, "balance_stale_after_days": 30}
        config_path.write_text(json.dumps(config))
        shutil.copy(EXAMPLES_DIR / 'catalog.json', catalog_path)
        shutil.copy(EXAMPLES_DIR / 'wallet.json', wallet_path)
        
        code, out, err = run_lookup(['validate', '--config', str(config_path)], cwd=tmpdir)
        assert code == 2, f"Expected 2, got {code}: {err}"
        assert 'path_in_git' in err
        print("✓ test_config_path_outside_git")

def test_schema_rejects_unknown_fields():
    """Unknown fields in JSON are rejected."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path, _, _ = setup_test_fixture(tmpdir)
        catalog_path = tmpdir / 'catalog.json'
        catalog = json.loads(catalog_path.read_text())
        catalog['unknown_field'] = 'not allowed'
        catalog_path.write_text(json.dumps(catalog))
        
        code, out, err = run_lookup(['validate', '--config', str(config_path)], cwd=tmpdir)
        assert code == 2, f"Expected 2, got {code}: {err}"
        print("✓ test_schema_rejects_unknown_fields")

def test_no_network_calls():
    """Verify no network imports in engine."""
    script_path = SCRIPTS_DIR / 'voucher_lookup.py'
    source = script_path.read_text()
    # Engine uses urllib.parse only for URL structural validation (no fetch)
    # No urllib.request, urllib.error, socket, subprocess
    assert 'urllib.request' not in source
    assert 'urllib.error' not in source
    assert 'http.client' not in source
    assert 'socket' not in source
    assert 'requests' not in source
    assert 'aiohttp' not in source
    assert 'subprocess' not in source or 'subprocess.' not in source
    # Check no subprocess import statement
    assert 'import subprocess' not in source
    assert 'from subprocess' not in source
    print("✓ test_no_network_calls")

if __name__ == '__main__':
    # Run all tests
    test_validate_success()
    test_validate_missing_file()
    test_lookup_kravitz_physical_supported()
    test_lookup_kravitz_hebrew_alias()
    test_lookup_merchant_ambiguous()
    test_lookup_merchant_not_found()
    test_lookup_fox_home_conditional()
    test_lookup_zara_excluded()
    test_lookup_ksp_online_only()
    test_lookup_branch_context()
    test_lookup_balance_zero_unavailable()
    test_lookup_balance_unknown()
    test_lookup_merchant_id()
    test_lookup_merchant_id_and_name_conflict()
    test_lookup_show_balances()
    test_lookup_text_format()
    test_config_path_outside_git()
    test_schema_rejects_unknown_fields()
    test_no_network_calls()
    print("\n✅ All tests passed!")