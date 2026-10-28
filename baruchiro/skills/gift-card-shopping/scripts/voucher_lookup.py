#!/usr/bin/env python3
"""
merchant-voucher-lookup — Local reverse lookup engine for vouchers/merchants.
Stdlib only, no network, no subprocess, no persistent state.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Constants & Types
# =============================================================================

SCHEMA_VERSION = 1
ID_PATTERN = r'^[a-z][a-z0-9_-]{0,63}$'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB
MAX_NAME_LEN = 120
MAX_TEXT_LEN = 1000

OUTCOME_ORDER = [
    'supported_candidate',
    'conditional',
    'conflict',
    'excluded',
    'unavailable',
    'unknown',
]

REASON_CODES = {
    'holding_inactive',
    'holding_expired',
    'reported_zero',
    'expiry_unknown',
    'balance_unknown',
    'balance_stale',
    'context_missing',
    'conditions_unresolved',
    'evidence_unverified',
    'evidence_stale',
    'conflicting_rules',
    'explicit_exclusion',
    'negative_lead',
    'no_applicable_rule',
}

VALID_KINDS = {'stored_value', 'membership', 'benefit'}
VALID_EFFECTS = {'allow', 'deny'}
VALID_BENEFIT_TYPES = {'redemption', 'discount', 'cashback'}
VALID_VERIFICATION = {'verified', 'unverified'}
VALID_AUTHORITIES = {'issuer_official', 'merchant_official', 'secondary'}
VALID_CHANNELS = {'physical', 'online', 'marketplace'}
VALID_STATUSES = {'active', 'inactive'}

# =============================================================================
# Exceptions
# =============================================================================

class VoucherError(Exception):
    def __init__(self, code: str, path: str):
        self.code = code
        self.path = path
        super().__init__(f"{code}: {path}")

# =============================================================================
# Data Classes (for internal structure)
# =============================================================================

@dataclass
class Config:
    schema_version: int
    catalog_path: str
    wallet_path: str
    cache_dir: str
    stale_after_days: int
    balance_stale_after_days: int

@dataclass
class Merchant:
    id: str
    name: str
    aliases: list[str]

@dataclass
class Product:
    id: str
    program_id: str
    name: str
    kind: str

@dataclass
class Holding:
    id: str
    label: str
    product_id: str
    kind: str
    status: str
    expires_on: Optional[str]
    balance: Optional[dict]

@dataclass
class Rule:
    id: str
    product_id: str
    merchant_id: str
    effect: str
    benefit_type: str
    scope: dict
    conditions: list[str]
    verification: str
    source_ids: list[str]
    valid_from: Optional[str]
    valid_until: Optional[str]

@dataclass
class Source:
    id: str
    url: str
    publisher: str
    authority: str
    checked_at: str
    evidence_excerpt: str

@dataclass
class Catalog:
    schema_version: int
    data_kind: str
    issuers: list[dict]
    programs: list[dict]
    products: list[Product]
    merchants: list[Merchant]
    sources: list[Source]
    rules: list[Rule]

@dataclass
class Wallet:
    schema_version: int
    data_kind: str
    holdings: list[Holding]

# =============================================================================
# Utility Functions
# =============================================================================

def normalize_name(s: str) -> str:
    """Normalize for matching: NFKC, casefold, trim, collapse whitespace."""
    import unicodedata
    s = unicodedata.normalize('NFKC', s)
    s = s.casefold()
    s = ' '.join(s.split())
    return s

def parse_date(s: Optional[str]) -> Optional[date]:
    if s is None:
        return None
    return datetime.strptime(s, '%Y-%m-%d').date()

def parse_rfc3339(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def is_fresh(checked_at: str, stale_after_days: int, now: datetime) -> bool:
    checked = parse_rfc3339(checked_at)
    delta = now - checked
    return delta.days <= stale_after_days

def validate_id(value: str, path: str) -> None:
    import re
    if not re.match(ID_PATTERN, value):
        raise VoucherError('invalid_id', path)

def validate_string(value: str, max_len: int, path: str) -> None:
    if not isinstance(value, str):
        raise VoucherError('invalid_type', path)
    if len(value) > max_len:
        raise VoucherError('string_too_long', path)
    if any(ord(c) < 32 for c in value):
        raise VoucherError('control_char', path)

def validate_url(url: str, path: str) -> None:
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
    except Exception:
        raise VoucherError('invalid_url', path)
    if p.scheme != 'https':
        raise VoucherError('url_not_https', path)
    if p.username or p.password:
        raise VoucherError('url_userinfo', path)
    if p.query or p.fragment:
        raise VoucherError('url_query_fragment', path)
    host = p.hostname or ''
    if host in ('localhost', '127.0.0.1', '::1') or host.replace('.', '').isdigit():
        raise VoucherError('url_localhost_ip', path)
    if '.' not in host:
        raise VoucherError('url_single_label', path)

def canonicalize_path(p: Path, base: Path) -> Path:
    """Resolve to absolute, resolve symlinks, return canonical path."""
    try:
        return (base / p).resolve(strict=False)
    except Exception:
        raise VoucherError('path_resolve', str(p))

def check_git_boundary(path: Path) -> None:
    """Ensure path is not inside any .git directory (including worktrees)."""
    current = path
    while current != current.parent:
        if (current / '.git').exists():
            raise VoucherError('path_in_git', str(path))
        current = current.parent

def read_json_file(path: Path, max_size: int = MAX_FILE_SIZE) -> dict:
    if path.stat().st_size > max_size:
        raise VoucherError('file_too_large', str(path))
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raise VoucherError('utf8_decode', str(path))
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise VoucherError('json_decode', f"{path}: {e}")
    return data

def check_unknown_fields(obj: dict, allowed: set[str], path: str) -> None:
    """Raise VoucherError if object has keys not in allowed set."""
    for key in obj:
        if key not in allowed:
            raise VoucherError('unknown_field', f"{path}.{key}")

# =============================================================================
# Validation & Loading
# =============================================================================

def load_config(config_path: Path) -> Config:
    data = read_json_file(config_path)
    check_unknown_fields(data, {'schema_version', 'catalog_path', 'wallet_path', 'cache_dir', 'stale_after_days', 'balance_stale_after_days'}, 'config')
    if data.get('schema_version') != SCHEMA_VERSION:
        raise VoucherError('schema_version', 'config.schema_version')
    
    base = config_path.parent
    catalog_path = canonicalize_path(Path(data['catalog_path']), base)
    wallet_path = canonicalize_path(Path(data['wallet_path']), base)
    cache_dir = canonicalize_path(Path(data['cache_dir']), base)
    
    for p in (catalog_path, wallet_path):
        check_git_boundary(p)
        if not p.is_file():
            raise VoucherError('not_file', str(p))
    check_git_boundary(cache_dir)
    
    stale_after = data.get('stale_after_days', 30)
    balance_stale = data.get('balance_stale_after_days', 30)
    if not (1 <= stale_after <= 365):
        raise VoucherError('stale_out_of_range', 'config.stale_after_days')
    if not (1 <= balance_stale <= 365):
        raise VoucherError('stale_out_of_range', 'config.balance_stale_after_days')
    
    return Config(
        schema_version=SCHEMA_VERSION,
        catalog_path=str(catalog_path),
        wallet_path=str(wallet_path),
        cache_dir=str(cache_dir),
        stale_after_days=stale_after,
        balance_stale_after_days=balance_stale,
    )

def load_catalog(catalog_path: Path, config: Config) -> Catalog:
    data = read_json_file(catalog_path)
    check_unknown_fields(data, {'schema_version', 'data_kind', 'issuers', 'programs', 'products', 'merchants', 'sources', 'rules'}, 'catalog')
    if data.get('schema_version') != SCHEMA_VERSION:
        raise VoucherError('schema_version', 'catalog.schema_version')
    data_kind = data.get('data_kind')
    if data_kind not in ('real', 'synthetic'):
        raise VoucherError('invalid_data_kind', 'catalog.data_kind')
    
    # Build lookup maps
    issuers = {i['id']: i for i in data.get('issuers', [])}
    programs = {p['id']: p for p in data.get('programs', [])}
    products = {p['id']: p for p in data.get('products', [])}
    merchants = {m['id']: m for m in data.get('merchants', [])}
    sources = {s['id']: s for s in data.get('sources', [])}
    rules = data.get('rules', [])
    
    # Validate cross-refs and uniqueness
    seen_ids = set()
    for table_name, table in [('issuers', issuers), ('programs', programs), 
                               ('products', products), ('merchants', merchants),
                               ('sources', sources)]:
        for id_, obj in table.items():
            validate_id(id_, f'{table_name}.{id_}')
            if id_ in seen_ids:
                raise VoucherError('duplicate_id', f'{table_name}.{id_}')
            seen_ids.add(id_)
    
    for r in rules:
        validate_id(r['id'], f'rules.{r["id"]}')
        if r['id'] in seen_ids:
            raise VoucherError('duplicate_id', f'rules.{r["id"]}')
        seen_ids.add(r['id'])
    
    # Validate issuers
    for i in issuers.values():
        validate_string(i['name'], MAX_NAME_LEN, f"issuers.{i['id']}.name")
    
    # Validate programs
    for p in programs.values():
        validate_string(p['name'], MAX_NAME_LEN, f"programs.{p['id']}.name")
        if p['issuer_id'] not in issuers:
            raise VoucherError('broken_ref', f"programs.{p['id']}.issuer_id")
    
    # Validate products
    product_objs = []
    for p in products.values():
        validate_string(p['name'], MAX_NAME_LEN, f"products.{p['id']}.name")
        if p['program_id'] not in programs:
            raise VoucherError('broken_ref', f"products.{p['id']}.program_id")
        if p['kind'] not in VALID_KINDS:
            raise VoucherError('invalid_enum', f"products.{p['id']}.kind")
        product_objs.append(Product(p['id'], p['program_id'], p['name'], p['kind']))
    
    # Validate merchants
    merchant_objs = []
    for m in merchants.values():
        validate_string(m['name'], MAX_NAME_LEN, f"merchants.{m['id']}.name")
        for alias in m.get('aliases', []):
            validate_string(alias, MAX_NAME_LEN, f"merchants.{m['id']}.aliases")
        merchant_objs.append(Merchant(m['id'], m['name'], m.get('aliases', [])))
    
    # Validate sources
    source_objs = []
    for s in sources.values():
        validate_string(s['publisher'], MAX_NAME_LEN, f"sources.{s['id']}.publisher")
        if s['authority'] not in VALID_AUTHORITIES:
            raise VoucherError('invalid_enum', f"sources.{s['id']}.authority")
        validate_url(s['url'], f"sources.{s['id']}.url")
        try:
            parse_rfc3339(s['checked_at'])
        except Exception:
            raise VoucherError('invalid_rfc3339', f"sources.{s['id']}.checked_at")
        validate_string(s['evidence_excerpt'], MAX_TEXT_LEN, f"sources.{s['id']}.evidence_excerpt")
        source_objs.append(Source(s['id'], s['url'], s['publisher'], s['authority'], 
                                  s['checked_at'], s['evidence_excerpt']))
    
    # Validate rules
    rule_objs = []
    for r in rules:
        if r['product_id'] not in products:
            raise VoucherError('broken_ref', f"rules.{r['id']}.product_id")
        if r['merchant_id'] not in merchants:
            raise VoucherError('broken_ref', f"rules.{r['id']}.merchant_id")
        if r['effect'] not in VALID_EFFECTS:
            raise VoucherError('invalid_enum', f"rules.{r['id']}.effect")
        if r['benefit_type'] not in VALID_BENEFIT_TYPES:
            raise VoucherError('invalid_enum', f"rules.{r['id']}.benefit_type")
        if r['verification'] not in VALID_VERIFICATION:
            raise VoucherError('invalid_enum', f"rules.{r['id']}.verification")
        
        # scope
        scope = r['scope']
        channels = scope.get('channels', [])
        if not channels or not all(c in VALID_CHANNELS for c in channels):
            raise VoucherError('invalid_scope', f"rules.{r['id']}.scope.channels")
        branch_ids = scope.get('branch_ids')
        if branch_ids is not None and not isinstance(branch_ids, list):
            raise VoucherError('invalid_type', f"rules.{r['id']}.scope.branch_ids")
        seller_ids = scope.get('seller_ids')
        if seller_ids is not None and not isinstance(seller_ids, list):
            raise VoucherError('invalid_type', f"rules.{r['id']}.scope.seller_ids")
        
        conditions = r.get('conditions', [])
        for cond in conditions:
            validate_string(cond, MAX_TEXT_LEN, f"rules.{r['id']}.conditions")
        
        source_ids = r.get('source_ids', [])
        if r['verification'] == 'verified' and not source_ids:
            raise VoucherError('verified_no_sources', f"rules.{r['id']}")
        for sid in source_ids:
            if sid not in sources:
                raise VoucherError('broken_ref', f"rules.{r['id']}.source_ids")
        if len(source_ids) != len(set(source_ids)):
            raise VoucherError('duplicate_source_ids', f"rules.{r['id']}")
        
        vf = r.get('valid_from')
        vu = r.get('valid_until')
        if vf is not None:
            try:
                parse_date(vf)
            except Exception:
                raise VoucherError('invalid_date', f"rules.{r['id']}.valid_from")
        if vu is not None:
            try:
                parse_date(vu)
            except Exception:
                raise VoucherError('invalid_date', f"rules.{r['id']}.valid_until")
        if vf and vu and parse_date(vf) > parse_date(vu):
            raise VoucherError('date_range_invalid', f"rules.{r['id']}")
        
        rule_objs.append(Rule(
            r['id'], r['product_id'], r['merchant_id'], r['effect'],
            r['benefit_type'], scope, conditions, r['verification'],
            source_ids, vf, vu
        ))
    
    return Catalog(
        schema_version=SCHEMA_VERSION,
        data_kind=data_kind,
        issuers=list(issuers.values()),
        programs=list(programs.values()),
        products=product_objs,
        merchants=merchant_objs,
        sources=source_objs,
        rules=rule_objs,
    )

def load_wallet(wallet_path: Path, catalog: Catalog) -> Wallet:
    data = read_json_file(wallet_path)
    check_unknown_fields(data, {'schema_version', 'data_kind', 'holdings'}, 'wallet')
    if data.get('schema_version') != SCHEMA_VERSION:
        raise VoucherError('schema_version', 'wallet.schema_version')
    data_kind = data.get('data_kind')
    if data_kind not in ('real', 'synthetic'):
        raise VoucherError('invalid_data_kind', 'wallet.data_kind')
    
    product_ids = {p.id for p in catalog.products}
    product_kind = {p.id: p.kind for p in catalog.products}
    
    holdings = []
    seen_ids = set()
    for h in data.get('holdings', []):
        validate_id(h['id'], f"holdings.{h['id']}")
        if h['id'] in seen_ids:
            raise VoucherError('duplicate_id', f"holdings.{h['id']}")
        seen_ids.add(h['id'])
        
        validate_string(h['label'], MAX_NAME_LEN, f"holdings.{h['id']}.label")
        if h['product_id'] not in product_ids:
            raise VoucherError('broken_ref', f"holdings.{h['id']}.product_id")
        if h['kind'] not in VALID_KINDS:
            raise VoucherError('invalid_enum', f"holdings.{h['id']}.kind")
        if h['kind'] != product_kind[h['product_id']]:
            raise VoucherError('kind_mismatch', f"holdings.{h['id']}.kind")
        if h['status'] not in VALID_STATUSES:
            raise VoucherError('invalid_enum', f"holdings.{h['id']}.status")
        
        expires = h.get('expires_on')
        if expires is not None:
            try:
                parse_date(expires)
            except Exception:
                raise VoucherError('invalid_date', f"holdings.{h['id']}.expires_on")
        
        balance = h.get('balance')
        if balance is not None:
            if h['kind'] != 'stored_value':
                raise VoucherError('balance_not_allowed', f"holdings.{h['id']}.balance")
            if not isinstance(balance.get('amount_minor'), int) or balance['amount_minor'] < 0:
                raise VoucherError('invalid_balance', f"holdings.{h['id']}.balance.amount_minor")
            if not isinstance(balance.get('currency'), str) or len(balance['currency']) != 3 or not balance['currency'].isupper():
                raise VoucherError('invalid_currency', f"holdings.{h['id']}.balance.currency")
            try:
                parse_rfc3339(balance['reported_at'])
            except Exception:
                raise VoucherError('invalid_rfc3339', f"holdings.{h['id']}.balance.reported_at")
            if balance.get('kind') != 'user_reported':
                raise VoucherError('invalid_enum', f"holdings.{h['id']}.balance.kind")
        else:
            if h['kind'] == 'stored_value':
                pass  # null allowed
            else:
                if balance is not None:
                    raise VoucherError('balance_not_allowed', f"holdings.{h['id']}.balance")
        
        holdings.append(Holding(
            h['id'], h['label'], h['product_id'], h['kind'],
            h['status'], expires, balance
        ))
    
    return Wallet(SCHEMA_VERSION, data_kind, holdings)

# =============================================================================
# Merchant Resolution
# =============================================================================

def resolve_merchant(catalog: Catalog, name: Optional[str], merchant_id: Optional[str]) -> tuple[Optional[Merchant], list[Merchant]]:
    if merchant_id:
        m = next((m for m in catalog.merchants if m.id == merchant_id), None)
        return (m, []) if m else (None, [])
    
    if not name:
        raise VoucherError('missing_merchant', 'lookup.merchant')
    
    norm = normalize_name(name)
    matches = []
    for m in catalog.merchants:
        if normalize_name(m.name) == norm:
            matches.append(m)
        elif any(normalize_name(a) == norm for a in m.aliases):
            matches.append(m)
    
    if len(matches) == 1:
        return (matches[0], [])
    elif len(matches) > 1:
        return (None, matches)
    return (None, [])

# =============================================================================
# Rule Evaluation
# =============================================================================

@dataclass
class EvalContext:
    merchant: Optional[Merchant]
    channel: Optional[str]
    branch_id: Optional[str]
    seller_id: Optional[str]
    eval_date: date
    now: datetime

@dataclass
class RuleMatch:
    rule: Rule
    scope_match: str  # matches, needs_context, does_not_match
    freshness: str    # fresh, stale, unknown
    source_info: dict

def evaluate_scope(rule: Rule, ctx: EvalContext) -> str:
    scope = rule.scope
    channels = scope.get('channels', [])
    branch_ids = scope.get('branch_ids')
    seller_ids = scope.get('seller_ids')
    
    # Channel
    if ctx.channel:
        if ctx.channel not in channels:
            return 'does_not_match'
    else:
        if channels != ['physical', 'online', 'marketplace']:  # not all channels
            return 'needs_context'
    
    # Branch
    if branch_ids is not None:
        if ctx.branch_id:
            if ctx.branch_id not in branch_ids:
                return 'does_not_match'
        else:
            return 'needs_context'
    
    # Seller
    if seller_ids is not None:
        if ctx.seller_id:
            if ctx.seller_id not in seller_ids:
                return 'does_not_match'
        else:
            return 'needs_context'
    
    return 'matches'

def evaluate_freshness(rule: Rule, catalog: Catalog, config: Config, now: datetime) -> str:
    if rule.verification != 'verified':
        return 'unknown'
    
    official_sources = [s for s in catalog.sources if s.id in rule.source_ids and s.authority in ('issuer_official', 'merchant_official')]
    if not official_sources:
        return 'unknown'
    
    for s in official_sources:
        if is_fresh(s.checked_at, config.stale_after_days, now):
            return 'fresh'
    return 'stale'

def rule_applies_on_date(rule: Rule, eval_date: date) -> bool:
    if rule.valid_from and parse_date(rule.valid_from) > eval_date:
        return False
    if rule.valid_until and parse_date(rule.valid_until) < eval_date:
        return False
    return True

def holding_active(holding: Holding, eval_date: date) -> tuple[bool, list[str]]:
    reasons = []
    if holding.status != 'active':
        reasons.append('holding_inactive')
        return False, reasons
    if holding.expires_on and parse_date(holding.expires_on) < eval_date:
        reasons.append('holding_expired')
        return False, reasons
    return True, reasons

def balance_state(holding: Holding, config: Config, now: datetime) -> tuple[str, str, list[str]]:
    reasons = []
    if holding.kind != 'stored_value':
        return 'not_applicable', 'not_applicable', reasons
    
    bal = holding.balance
    if bal is None:
        return 'unknown', 'unknown', ['balance_unknown']
    
    if bal['amount_minor'] == 0:
        reasons.append('reported_zero')
        return 'reported_zero', 'unknown', reasons
    
    reported = parse_rfc3339(bal['reported_at'])
    delta = now - reported
    if delta.days > config.balance_stale_after_days:
        reasons.append('balance_stale')
        return 'reported_positive', 'stale', reasons
    
    return 'reported_positive', 'fresh', reasons

def evaluate_holding(holding: Holding, merchant: Merchant, catalog: Catalog, config: Config, ctx: EvalContext) -> dict:
    # Filter rules for this holding's product and merchant
    relevant_rules = [r for r in catalog.rules 
                      if r.product_id == holding.product_id and r.merchant_id == merchant.id
                      and rule_applies_on_date(r, ctx.eval_date)]
    
    if not relevant_rules:
        return {
            'outcome': 'unknown',
            'reason_codes': ['no_applicable_rule'],
            'rules': [],
        }
    
    # Evaluate each rule
    rule_results = []
    for rule in relevant_rules:
        scope_match = evaluate_scope(rule, ctx)
        freshness = evaluate_freshness(rule, catalog, config, ctx.now)
        
        source_info = {
            'rule_id': rule.id,
            'effect': rule.effect,
            'benefit_type': rule.benefit_type,
            'scope': rule.scope,
            'conditions': rule.conditions,
            'verification': rule.verification,
            'source_urls': [s.url for s in catalog.sources if s.id in rule.source_ids],
            'source_authorities': [s.authority for s in catalog.sources if s.id in rule.source_ids],
            'source_checked_at': [s.checked_at for s in catalog.sources if s.id in rule.source_ids],
            'valid_from': rule.valid_from,
            'valid_until': rule.valid_until,
            'freshness': freshness,
            'scope_match': scope_match,
        }
        rule_results.append(RuleMatch(rule, scope_match, freshness, source_info))
    
    # Separate allow/deny
    allows = [rr for rr in rule_results if rr.rule.effect == 'allow' and rr.scope_match == 'matches']
    allows_needs_context = [rr for rr in rule_results if rr.rule.effect == 'allow' and rr.scope_match == 'needs_context']
    denies = [rr for rr in rule_results if rr.rule.effect == 'deny' and rr.scope_match == 'matches']
    
    # Holding active check
    active, active_reasons = holding_active(holding, ctx.eval_date)
    bal_state, bal_fresh, bal_reasons = balance_state(holding, config, ctx.now)
    all_reasons = active_reasons + bal_reasons
    
    # Outcome decision
    if not active:
        return {'outcome': 'unavailable', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
    
    if holding.kind == 'stored_value' and holding.balance and holding.balance['amount_minor'] == 0:
        return {'outcome': 'unavailable', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
    
    # Conflict: verified allow + verified deny both match
    verified_allows = [rr for rr in allows if rr.rule.verification == 'verified']
    verified_denies = [rr for rr in denies if rr.rule.verification == 'verified']
    if verified_allows and verified_denies:
        all_reasons.append('conflicting_rules')
        return {'outcome': 'conflict', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
    
    # Excluded: verified fresh deny, no overlapping verified allow
    fresh_verified_denies = [rr for rr in verified_denies if rr.freshness == 'fresh']
    if fresh_verified_denies and not verified_allows:
        all_reasons.append('explicit_exclusion')
        return {'outcome': 'excluded', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
    
    # Supported candidate: verified fresh allow, no conflict/deny, holding valid
    fresh_verified_allows = [rr for rr in verified_allows if rr.freshness == 'fresh']
    if fresh_verified_allows and not verified_denies:
        # Check conditions
        for rr in fresh_verified_allows:
            if rr.rule.conditions:
                all_reasons.append('conditions_unresolved')
                return {'outcome': 'conditional', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
        # Check expiry unknown
        if holding.expires_on is None:
            all_reasons.append('expiry_unknown')
        # Check balance unknown/stale
        if bal_state == 'unknown':
            all_reasons.append('balance_unknown')
        elif bal_fresh == 'stale':
            all_reasons.append('balance_stale')
        
        if all_reasons:
            return {'outcome': 'conditional', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
        
        return {'outcome': 'supported_candidate', 'reason_codes': [], 'rules': [rr.source_info for rr in rule_results]}
    
    # Conditional: allow exists but unverified/stale/missing context/conditions
    conditional_allows = allows + allows_needs_context
    if conditional_allows:
        for rr in conditional_allows:
            if rr.scope_match == 'needs_context':
                all_reasons.append('context_missing')
            if rr.rule.conditions:
                all_reasons.append('conditions_unresolved')
            if rr.rule.verification == 'unverified':
                all_reasons.append('evidence_unverified')
            elif rr.freshness == 'stale':
                all_reasons.append('evidence_stale')
        if holding.expires_on is None:
            all_reasons.append('expiry_unknown')
        if bal_state == 'unknown':
            all_reasons.append('balance_unknown')
        elif bal_fresh == 'stale':
            all_reasons.append('balance_stale')
        
        if not all_reasons:
            all_reasons.append('no_applicable_rule')
        return {'outcome': 'conditional', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}
    
    # Unknown: no applicable allow, or only stale/unverified deny
    if denies:
        for rr in denies:
            if rr.rule.verification == 'unverified' or rr.freshness == 'stale':
                all_reasons.append('negative_lead')
    else:
        all_reasons.append('no_applicable_rule')
    return {'outcome': 'unknown', 'reason_codes': all_reasons, 'rules': [rr.source_info for rr in rule_results]}

# =============================================================================
# Output Formatting
# =============================================================================

def format_text_output(result: dict, show_balances: bool) -> str:
    lines = []
    merchant = result.get('merchant')
    ctx = result.get('context', {})
    
    if merchant:
        lines.append(f"רשת: {merchant['name']} | ערוץ: {ctx.get('channel', 'לא צוין')} | תאריך הערכה: {result['evaluated_on']}")
    else:
        lines.append(f"ערוץ: {ctx.get('channel', 'לא צוין')} | תאריך הערכה: {result['evaluated_on']}")
    lines.append("")
    
    # Group by outcome
    by_outcome = {o: [] for o in OUTCOME_ORDER}
    for h in result.get('holdings', []):
        by_outcome[h['outcome']].append(h)
    
    # Supported candidates
    if by_outcome['supported_candidate']:
        lines.append("✅ מועמדים נתמכים (לפי מקור):")
        for h in by_outcome['supported_candidate']:
            bal_str = ""
            if show_balances and h.get('balance'):
                bal = h['balance']
                bal_str = f" — יתרה: {bal['amount_minor']/100:.2f} {bal['currency']}"
            lines.append(f"- {h['product_name']} ({h['label']}) — {h['kind']}. מקור: {[r['source_urls'][0] for r in h['rules'] if r['source_urls']][0] if h['rules'] else 'לא ידוע'}, נבדק {h['rules'][0]['source_checked_at'][0] if h['rules'] and h['rules'][0]['source_checked_at'] else 'לא ידוע'}. נדרשת בדיקת תנאים בקופה.{bal_str}")
        lines.append("")
    
    # Conditional
    if by_outcome['conditional']:
        lines.append("⚠ דורשים בירור:")
        for h in by_outcome['conditional']:
            reasons = ', '.join(h['reason_codes'])
            lines.append(f"- {h['product_name']} ({h['label']}) — {reasons}.")
        lines.append("")
    
    # Conflict
    if by_outcome['conflict']:
        lines.append("⚠ סתירה במידע:")
        for h in by_outcome['conflict']:
            lines.append(f"- {h['product_name']} ({h['label']}) — מקורות סותרים.")
        lines.append("")
    
    # Excluded
    if by_outcome['excluded']:
        lines.append("❌ מוחרגים:")
        for h in by_outcome['excluded']:
            lines.append(f"- {h['product_name']} ({h['label']}) — החרגה מאומתת.")
        lines.append("")
    
    # Unavailable
    if by_outcome['unavailable']:
        lines.append("❌ לא רלוונטיים:")
        for h in by_outcome['unavailable']:
            reasons = ', '.join(h['reason_codes'])
            lines.append(f"- {h['product_name']} ({h['label']}) — {reasons}.")
        lines.append("")
    
    # Unknown
    if by_outcome['unknown']:
        lines.append("❓ אין מידע:")
        for h in by_outcome['unknown']:
            reasons = ', '.join(h['reason_codes'])
            lines.append(f"- {h['product_name']} ({h['label']}) — {reasons}.")
        lines.append("")
    
    if result.get('data_kind') == 'synthetic':
        lines.append("נתונים סינתטיים — לא ראיית קבלה אמיתית")
    
    lines.append(f"לפי קטלוג מקומי נכון ל-{result['evaluated_on']}. לא התחייבות לקבלה בקופה. יש לאמת מול הרשת/המנפיק לפני תשלום.")
    return '\n'.join(lines)

# =============================================================================
# Commands
# =============================================================================

def cmd_validate(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser().resolve()
    try:
        config = load_config(config_path)
        load_catalog(Path(config.catalog_path), config)
        load_wallet(Path(config.wallet_path), load_catalog(Path(config.catalog_path), config))
        print("OK: config, catalog, wallet valid")
        return 0
    except VoucherError as e:
        print(f"ERROR: {e.code}: {e.path}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: io_error: {e}", file=sys.stderr)
        return 4

def cmd_lookup(args: argparse.Namespace) -> int:
    if args.merchant and args.merchant_id:
        print("ERROR: invalid_input: --merchant and --merchant-id are mutually exclusive", file=sys.stderr)
        return 2
    
    config_path = Path(args.config).expanduser().resolve()
    try:
        config = load_config(config_path)
        catalog = load_catalog(Path(config.catalog_path), config)
        wallet = load_wallet(Path(config.wallet_path), catalog)
    except VoucherError as e:
        print(f"ERROR: {e.code}: {e.path}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: io_error: {e}", file=sys.stderr)
        return 4
    
    # Resolve merchant
    merchant, candidates = resolve_merchant(catalog, args.merchant, args.merchant_id)
    
    # Build context
    eval_date = parse_date(args.on) if args.on else date.today()
    now = datetime.now(timezone.utc)
    
    ctx = EvalContext(
        merchant=merchant,
        channel=args.channel,
        branch_id=args.branch_id,
        seller_id=args.seller_id,
        eval_date=eval_date,
        now=now,
    )
    
    if candidates:
        result = {
            'schema_version': SCHEMA_VERSION,
            'status': 'merchant_ambiguous',
            'data_kind': catalog.data_kind,
            'evaluated_on': eval_date.isoformat(),
            'observed_at': now.isoformat(),
            'merchant': None,
            'context': {'channel': args.channel, 'branch_id': args.branch_id, 'seller_id': args.seller_id, 'on': eval_date.isoformat()},
            'merchant_candidates': [{'id': m.id, 'name': m.name} for m in candidates],
            'holdings': [],
            'warnings': [],
        }
    elif merchant is None:
        result = {
            'schema_version': SCHEMA_VERSION,
            'status': 'merchant_not_found',
            'data_kind': catalog.data_kind,
            'evaluated_on': eval_date.isoformat(),
            'observed_at': now.isoformat(),
            'merchant': None,
            'context': {'channel': args.channel, 'branch_id': args.branch_id, 'seller_id': args.seller_id, 'on': eval_date.isoformat()},
            'merchant_candidates': [],
            'holdings': [],
            'warnings': [],
        }
    else:
        # Evaluate each holding
        holdings_out = []
        for holding in wallet.holdings:
            eval_result = evaluate_holding(holding, merchant, catalog, config, ctx)
            
            # Find product name
            product = next((p for p in catalog.products if p.id == holding.product_id), None)
            product_name = product.name if product else holding.product_id
            
            holding_out = {
                'holding_id': holding.id,
                'label': holding.label,
                'product_id': holding.product_id,
                'product_name': product_name,
                'kind': holding.kind,
                'outcome': eval_result['outcome'],
                'reason_codes': eval_result['reason_codes'],
                'expires_on': holding.expires_on,
                'balance_state': 'unknown',
                'balance_freshness': 'unknown',
                'rules': eval_result['rules'],
                'balance': None,
            }
            
            # Balance state/freshness
            if holding.kind == 'stored_value':
                if holding.balance is None:
                    holding_out['balance_state'] = 'unknown'
                    holding_out['balance_freshness'] = 'unknown'
                elif holding.balance['amount_minor'] == 0:
                    holding_out['balance_state'] = 'reported_zero'
                    holding_out['balance_freshness'] = 'unknown'
                else:
                    holding_out['balance_state'] = 'reported_positive'
                    reported = parse_rfc3339(holding.balance['reported_at'])
                    delta = now - reported
                    holding_out['balance_freshness'] = 'fresh' if delta.days <= config.balance_stale_after_days else 'stale'
            else:
                holding_out['balance_state'] = 'not_applicable'
                holding_out['balance_freshness'] = 'not_applicable'
            
            if args.show_balances:
                holding_out['balance'] = holding.balance
            
            holdings_out.append(holding_out)
        
        # Sort by outcome order, then normalized label, then holding_id
        def sort_key(h):
            return (OUTCOME_ORDER.index(h['outcome']), normalize_name(h['label']), h['holding_id'])
        holdings_out.sort(key=sort_key)
        
        result = {
            'schema_version': SCHEMA_VERSION,
            'status': 'ok',
            'data_kind': catalog.data_kind,
            'evaluated_on': eval_date.isoformat(),
            'observed_at': now.isoformat(),
            'merchant': {'id': merchant.id, 'name': merchant.name},
            'context': {'channel': args.channel, 'branch_id': args.branch_id, 'seller_id': args.seller_id, 'on': eval_date.isoformat()},
            'merchant_candidates': [],
            'holdings': holdings_out,
            'warnings': [],
        }
    
    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text_output(result, args.show_balances))
    
    # Exit code
    if result['status'] in ('merchant_ambiguous', 'merchant_not_found'):
        return 3
    return 0

# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(prog='merchant_voucher_lookup', description='Local voucher/merchant reverse lookup')
    sub = parser.add_subparsers(dest='command', required=True)
    
    p_val = sub.add_parser('validate', help='Validate config, catalog, wallet')
    p_val.add_argument('--config', required=True, help='Path to config.json')
    
    p_lookup = sub.add_parser('lookup', help='Lookup vouchers for a merchant')
    p_lookup.add_argument('--config', required=True, help='Path to config.json')
    p_lookup.add_argument('--merchant', help='Merchant name (Hebrew or Latin)')
    p_lookup.add_argument('--merchant-id', help='Merchant ID (exclusive with --merchant)')
    p_lookup.add_argument('--channel', choices=['physical', 'online', 'marketplace'], help='Purchase channel')
    p_lookup.add_argument('--branch-id', help='Branch ID')
    p_lookup.add_argument('--seller-id', help='Seller ID')
    p_lookup.add_argument('--on', help='Evaluation date YYYY-MM-DD (default: today)')
    p_lookup.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    p_lookup.add_argument('--show-balances', action='store_true', help='Show balance amounts (requires explicit user request)')
    
    args = parser.parse_args()
    
    if args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'lookup':
        return cmd_lookup(args)
    return 2

if __name__ == '__main__':
    sys.exit(main())