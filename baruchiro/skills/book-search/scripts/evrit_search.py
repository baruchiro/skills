#!/usr/bin/env python3
"""evrit discovery entry point; automation is explicitly unavailable."""
from _search_common import manual_result, run_cli
from evrit_verify import (fetch, extract_json_ld, find_book_json_ld, parse_product_page,
                          parse_author_page, search_via_ddg)


def search(query, mode='title', max_pages=3):
    return manual_result('evrit', query, mode)


if __name__ == '__main__':
    import sys
    from evrit_verify import main as legacy_main
    # Compatibility only: older product/author-URL verification commands.
    args = sys.argv[1:]
    legacy_mode = args[args.index('--mode') + 1] if '--mode' in args and args.index('--mode') + 1 < len(args) else None
    legacy = legacy_mode in ('product', 'search') or (args and args[0].startswith('https://'))
    if legacy:
        legacy_main()
    else:
        raise SystemExit(run_cli('evrit', search))
