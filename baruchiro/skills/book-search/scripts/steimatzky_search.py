#!/usr/bin/env python3
"""steimatzky discovery entry point; automation is explicitly unavailable."""
from _search_common import manual_result, run_cli


def search(query, mode='title', max_pages=3):
    return manual_result('steimatzky', query, mode)


if __name__ == '__main__':
    raise SystemExit(run_cli('steimatzky', search))
