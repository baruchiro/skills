"""Shared CLI/result contract. Source implementations stay in their own files."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sources():
    return json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))


def base_result(provider, query, mode):
    item = sources()[provider]
    return {'provider': provider, 'query': query, 'mode': mode,
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'capability': item['capability'], 'reference': item['reference'],
            'entry_url': item['entry_url'], 'complete': False, 'status': 'incomplete',
            'products': [], 'count': 0, 'errors': []}


def manual_result(provider, query, mode):
    result = base_result(provider, query, mode)
    result['status'] = 'manual_required'
    result['errors'] = ['Automated title/author search is not implemented. Follow the source reference with web/browser tools; this is not a completed search or evidence of absence.']
    return result


def run_cli(provider, search, argv=None):
    parser = argparse.ArgumentParser(description=f'{provider}: title/author discovery; see references/{provider}.md')
    parser.add_argument('query')
    parser.add_argument('--mode', choices=['title', 'author'], default='title')
    parser.add_argument('--max-pages', type=int, default=3, help='Page cap, 1-10. Manual sources perform no network calls.')
    parser.add_argument('--output', type=Path, help='Optional JSON file outside this package')
    args = parser.parse_args(argv)
    if not args.query.strip() or len(args.query) > 100 or not 1 <= args.max_pages <= 10:
        parser.error('Query must be 1-100 characters; max-pages must be 1-10')
    if args.output and args.output.resolve().is_relative_to(ROOT):
        parser.error('Keep search output outside the skill package')
    result = base_result(provider, args.query, args.mode)
    try:
        result.update(search(args.query, args.mode, args.max_pages))
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        result['complete'] = False
    if result['complete']:
        result['status'] = 'complete'
    elif result['status'] != 'manual_required':
        result['status'] = 'incomplete'
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0 if result['complete'] else 2
