#!/usr/bin/env python3
"""Collect a reviewer's PR activity without making the agent rebuild the query logic."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import functools
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SEARCH_FIELDS = "number,title,author,createdAt,updatedAt,state,url"
LINK_RE = re.compile(r"https?://[^\s<>\")\]]+")
ROLE_FLAGS = {
    "reviewed": "--reviewed-by",
    "commented": "--commenter",
    "authored": "--author",
}
ROLE_QUALIFIERS = {
    "reviewed": "reviewed-by",
    "commented": "commenter",
    "authored": "author",
}


class CollectionError(RuntimeError):
    """A GitHub collection command failed."""


SEARCH_PAUSE_SECONDS = 2.1  # Search API allows 30 requests per minute
API_PAUSE_SECONDS = 0.5  # stay clear of GitHub's secondary (burst) rate limits
RATE_LIMIT_WAIT_SECONDS = 60
RATE_LIMIT_RETRIES = 3


def run_gh(args: list[str]) -> str:
    command = ["gh", *args]
    is_search = args[0] == "search" or "search/issues" in args
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        time.sleep(SEARCH_PAUSE_SECONDS if is_search else API_PAUSE_SECONDS)
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except FileNotFoundError as exc:
            raise CollectionError("GitHub CLI (`gh`) is not installed.") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or "unknown gh error"
            if "rate limit" in detail.lower() and attempt < RATE_LIMIT_RETRIES:
                print(
                    f"rate limited; waiting {RATE_LIMIT_WAIT_SECONDS}s",
                    file=sys.stderr,
                )
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
                continue
            raise CollectionError(f"`{' '.join(command)}` failed: {detail}") from exc
    raise AssertionError("unreachable")


def gh_json(args: list[str]) -> Any:
    output = run_gh(args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise CollectionError(f"GitHub CLI returned invalid JSON: {exc}") from exc


def search_count(
    repo: str,
    login: str,
    role: str,
    created: tuple[dt.date, dt.date] | None = None,
) -> int:
    qualifier = f"{ROLE_QUALIFIERS[role]}:{login}"
    parts = [f"repo:{repo}", "is:pr", qualifier]
    if created:
        parts.append(f"created:{created[0].isoformat()}..{created[1].isoformat()}")
    result = gh_json(
        [
            "api",
            "--method",
            "GET",
            "search/issues",
            "-f",
            f"q={' '.join(parts)}",
            "-F",
            "per_page=1",
        ]
    )
    return int(result["total_count"])


def search_prs(
    repo: str,
    login: str,
    role: str,
    created: tuple[dt.date, dt.date] | None = None,
) -> list[dict[str, Any]]:
    args = [
        "search",
        "prs",
        "--repo",
        repo,
        ROLE_FLAGS[role],
        login,
        "--limit",
        "1000",
        "--json",
        SEARCH_FIELDS,
    ]
    if created:
        args.extend(
            ["--created", f"{created[0].isoformat()}..{created[1].isoformat()}"]
        )
    result = gh_json(args)
    if not isinstance(result, list):
        raise CollectionError(f"Expected a PR list for role `{role}`.")
    return result


def partitioned_search(
    repo: str,
    login: str,
    role: str,
    repo_created: dt.date,
    today: dt.date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    total = search_count(repo, login, role)
    if total < 1000:
        return search_prs(repo, login, role), [
            {"created": None, "reported_count": total, "complete": True}
        ]

    pending = [(repo_created, today)]
    ranges: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    while pending:
        start, end = pending.pop()
        count = search_count(repo, login, role, (start, end))
        if count < 1000:
            results.extend(search_prs(repo, login, role, (start, end)))
            ranges.append(
                {
                    "created": f"{start.isoformat()}..{end.isoformat()}",
                    "reported_count": count,
                    "complete": True,
                }
            )
            continue
        if start == end:
            ranges.append(
                {
                    "created": start.isoformat(),
                    "reported_count": count,
                    "complete": False,
                    "gap": "GitHub Search has at least 1,000 matching PRs on one day.",
                }
            )
            continue
        midpoint = start + (end - start) // 2
        pending.append((midpoint + dt.timedelta(days=1), end))
        pending.append((start, midpoint))

    by_number = {int(pr["number"]): pr for pr in results}
    return list(by_number.values()), sorted(
        ranges, key=lambda item: item["created"] or ""
    )


def counter_rows(values: list[Any], key: str) -> list[dict[str, Any]]:
    counts = collections.Counter(values)
    return [
        {key: value, "count": count}
        for value, count in sorted(
            counts.items(), key=lambda item: (-item[1], str(item[0]))
        )
    ]


def value_range(values: list[str]) -> dict[str, str] | None:
    return {"earliest": min(values), "latest": max(values)} if values else None


def area_of(repo: str, path: str | None) -> str:
    """Group a comment's file path into a coarse system area within its repo."""
    parts = [part for part in (path or "").split("/") if part]
    if not parts:
        return "(no path)"
    return "/".join([repo.split("/", 1)[1], *parts[:2]])


def write_comment_batches(
    comments: list[dict[str, Any]],
    comments_dir: Path,
    batch_size: int,
) -> list[dict[str, Any]]:
    """Shard human comments into ordered batch files the agent crunches one by one."""
    ordered = sorted(
        comments, key=lambda comment: (comment.get("created_at") or "", comment["id"])
    )
    batches: list[dict[str, Any]] = []
    for start in range(0, len(ordered), batch_size):
        chunk = ordered[start : start + batch_size]
        index = start // batch_size
        path = comments_dir / f"batch-{index:03d}.json"
        atomic_write_json(path, chunk)
        batches.append(
            {
                "index": index,
                "file": str(path),
                "count": len(chunk),
                "prs": sorted(
                    {(comment["repo"], comment["pr_number"]) for comment in chunk}
                ),
                "areas": counter_rows(
                    [area_of(comment["repo"], comment["path"]) for comment in chunk], "area"
                ),
                "created_range": value_range(
                    [comment["created_at"] for comment in chunk if comment.get("created_at")]
                ),
            }
        )
    return batches


@functools.cache
def load_ai_markers() -> tuple[str, ...]:
    marker_file = (
        Path(__file__).resolve().parents[3] / "shared" / "agent-reply-marker.txt"
    )
    reply_marker = marker_file.read_text(encoding="utf-8").strip()
    if not reply_marker:
        raise CollectionError(f"{marker_file} is empty; refusing to flag every comment.")
    return (
        reply_marker,
        "<!-- ai-review-result:",
        "<!-- ai-test-review-result:",
    )


def is_ai_comment(body: str) -> bool:
    return any(marker in body for marker in load_ai_markers())


def is_self(login: str | None, target: str) -> bool:
    return bool(login) and login.casefold() == target.casefold()


PR_BATCH_SIZE = 25
MY_REVIEWS_FIELDS = """
  reviews(author: $login, first: 100, states: [APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED]) {
    pageInfo { hasNextPage }
    nodes {
      databaseId state body submittedAt url
      comments(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          databaseId path line originalLine body createdAt updatedAt url
          replyTo { databaseId }
        }
      }
    }
  }
"""
MY_ISSUE_COMMENTS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    issueComments(first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        databaseId body createdAt updatedAt url
        repository { nameWithOwner }
        pullRequest { number }
      }
    }
  }
}
"""


def graphql(query: str, **variables: str) -> dict[str, Any]:
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args.extend(["-f", f"{key}={value}"])
    return gh_json(args)["data"]


def fetch_my_reviews(
    repo: str, login: str, numbers: list[int]
) -> tuple[list[tuple[int, dict[str, Any]]], list[int]]:
    """The login's submitted reviews (with their inline comments) on the given PRs.

    Filtered server-side by author, so other people's comments are never downloaded.
    """
    owner, name = repo.split("/", 1)
    found: list[tuple[int, dict[str, Any]]] = []
    truncated: list[int] = []
    for start in range(0, len(numbers), PR_BATCH_SIZE):
        batch = numbers[start : start + PR_BATCH_SIZE]
        aliases = "\n".join(
            f"pr{number}: pullRequest(number: {number}) {{ {MY_REVIEWS_FIELDS} }}"
            for number in batch
        )
        query = (
            "query($owner: String!, $name: String!, $login: String!) {"
            f" repository(owner: $owner, name: $name) {{ {aliases} }} }}"
        )
        repository = graphql(query, owner=owner, name=name, login=login)["repository"]
        for number in batch:
            pr = repository.get(f"pr{number}")
            if not pr:
                continue
            reviews = pr["reviews"]
            # shortcut: >100 reviews per PR or >100 comments per review are cut off and
            # reported in `truncated_prs`; paginate if that list is ever non-empty.
            if reviews["pageInfo"]["hasNextPage"] or any(
                review["comments"]["pageInfo"]["hasNextPage"]
                for review in reviews["nodes"]
            ):
                truncated.append(number)
            found.extend((number, review) for review in reviews["nodes"])
    return found, truncated


def fetch_my_pr_conversation_comments(login: str) -> list[dict[str, Any]]:
    """The login's own non-inline comments on pull requests (never issues), all repos."""
    comments: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        variables = {"login": login, **({"cursor": cursor} if cursor else {})}
        page = graphql(MY_ISSUE_COMMENTS_QUERY, **variables)["user"]["issueComments"]
        comments.extend(comment for comment in page["nodes"] if comment["pullRequest"])
        if not page["pageInfo"]["hasNextPage"]:
            return comments
        cursor = page["pageInfo"]["endCursor"]


def interaction(
    *,
    item_id: int,
    url: str | None,
    number: int,
    kind: str,
    body: str | None,
    created_at: str | None,
    updated_at: str | None,
    repo: str,
    prs: dict[int, dict[str, Any]],
    login: str,
    path: str | None = None,
    line: int | None = None,
    original_line: int | None = None,
    review_id: int | None = None,
    in_reply_to_id: int | None = None,
    review_state: str | None = None,
) -> dict[str, Any]:
    pr = prs.get(number, {})
    body = body or ""
    return {
        "id": item_id,
        "repo": repo,
        "html_url": url,
        "pr_number": number,
        "pr_url": pr.get("url", f"https://github.com/{repo}/pull/{number}"),
        "pr_title": pr.get("title"),
        "pr_author": pr.get("author"),
        "pr_state": pr.get("state"),
        "roles": sorted(pr.get("roles", [])),
        "kind": kind,
        "as_author": is_self(pr.get("author"), login),
        "path": path,
        "line": line,
        "original_line": original_line,
        "review_id": review_id,
        "in_reply_to_id": in_reply_to_id,
        "review_state": review_state,
        "created_at": created_at,
        "updated_at": updated_at,
        "body": body,
        "body_chars": len(body),
        "links": LINK_RE.findall(body),
        "ai_marked": is_ai_comment(body),
    }


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_summary(result: dict[str, Any], detail_output: Path) -> dict[str, Any]:
    candidates = []
    for candidate in result["candidate_selection"]["candidates"]:
        body = candidate["body"]
        compact = {
            key: value
            for key, value in candidate.items()
            if key not in {"body", "ai_marked"}
        }
        compact["body_preview"] = body[:500] + ("…" if len(body) > 500 else "")
        candidates.append(compact)
    return {
        "schema_version": result["schema_version"],
        "generated_at": result["generated_at"],
        "repositories": result["repositories"],
        "per_repo": result["per_repo"],
        "requested_reviewer": result["requested_reviewer"],
        "authenticated_login": result["authenticated_login"],
        "coverage_complete": result["coverage_complete"],
        "query_ranges": result["query_ranges"],
        "counts": result["counts"],
        "created_range": result["created_range"],
        "updated_range": result["updated_range"],
        "states": result["states"],
        "top_authors": result["authors"][:25],
        "role_combinations": result["role_combinations"],
        "area_counts": result["area_counts"],
        "kind_counts": result["kind_counts"],
        "author_side_counts": result["author_side_counts"],
        "verdict_summary": result["verdict_summary"],
        "comment_batches": result["comment_batches"],
        "candidate_selection": {
            "method": result["candidate_selection"]["method"],
            "limit": result["candidate_selection"]["limit"],
            "candidates": candidates,
        },
        "collection_levels": result["collection_levels"],
        "detail_output": str(detail_output),
    }


def collect_repo(repo: str, login: str, today: dt.date) -> dict[str, Any]:
    repo_info = gh_json(["api", f"repos/{repo}"])
    repo_created = dt.date.fromisoformat(repo_info["created_at"][:10])

    indexed: dict[str, list[dict[str, Any]]] = {}
    query_ranges: dict[str, list[dict[str, Any]]] = {}
    for role in ROLE_FLAGS:
        indexed[role], query_ranges[role] = partitioned_search(
            repo, login, role, repo_created, today
        )

    pr_by_number: dict[int, dict[str, Any]] = {}
    for role, role_prs in indexed.items():
        for source in role_prs:
            number = int(source["number"])
            author = source.get("author")
            entry = pr_by_number.setdefault(
                number,
                {
                    "repo": repo,
                    "number": number,
                    "title": source["title"],
                    "author": author.get("login") if isinstance(author, dict) else None,
                    "createdAt": source["createdAt"],
                    "updatedAt": source["updatedAt"],
                    "state": source["state"],
                    "url": source["url"],
                    "roles": set(),
                },
            )
            entry["roles"].add(role)

    prs = sorted(
        ({**entry, "roles": sorted(entry["roles"])} for entry in pr_by_number.values()),
        key=lambda entry: entry["number"],
    )
    normalized_prs = {entry["number"]: entry for entry in prs}
    my_reviews, truncated_prs = fetch_my_reviews(
        repo, login, sorted(normalized_prs, reverse=True)
    )
    context = {"repo": repo, "prs": normalized_prs, "login": login}

    reviews = [
        interaction(
            item_id=review["databaseId"],
            url=review["url"],
            number=number,
            kind="review_summary",
            body=review["body"],
            created_at=review["submittedAt"],
            updated_at=review["submittedAt"],
            review_id=review["databaseId"],
            review_state=review["state"],
            **context,
        )
        for number, review in my_reviews
    ]
    comments = [
        interaction(
            item_id=comment["databaseId"],
            url=comment["url"],
            number=number,
            kind="inline_reply" if comment["replyTo"] else "inline",
            body=comment["body"],
            created_at=comment["createdAt"],
            updated_at=comment["updatedAt"],
            path=comment["path"],
            line=comment["line"],
            original_line=comment["originalLine"],
            review_id=review["databaseId"],
            in_reply_to_id=(comment["replyTo"] or {}).get("databaseId"),
            **context,
        )
        for number, review in my_reviews
        for comment in review["comments"]["nodes"]
    ]
    return {
        "repo": repo,
        "indexed": indexed,
        "query_ranges": query_ranges,
        "prs": prs,
        "context": context,
        "truncated_prs": [(repo, number) for number in truncated_prs],
        "reviews": reviews,
        "comments": comments,
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    authenticated_login = run_gh(["api", "user", "--jq", ".login"]).strip()
    today = dt.datetime.now(dt.timezone.utc).date()
    repo_results = [collect_repo(repo, args.login, today) for repo in args.repo]
    by_repo = {result["repo"].casefold(): result for result in repo_results}

    conversation_comments = [
        interaction(
            item_id=comment["databaseId"],
            url=comment["url"],
            number=comment["pullRequest"]["number"],
            kind="conversation",
            body=comment["body"],
            created_at=comment["createdAt"],
            updated_at=comment["updatedAt"],
            **by_repo[comment["repository"]["nameWithOwner"].casefold()]["context"],
        )
        for comment in fetch_my_pr_conversation_comments(args.login)
        if comment["repository"]["nameWithOwner"].casefold() in by_repo
    ]

    prs = [pr for result in repo_results for pr in result["prs"]]
    reviews = [item for result in repo_results for item in result["reviews"]]
    comments = [item for result in repo_results for item in result["comments"]]
    truncated_prs = [item for result in repo_results for item in result["truncated_prs"]]
    indexed = {
        role: [pr for result in repo_results for pr in result["indexed"][role]]
        for role in ROLE_FLAGS
    }
    query_ranges = {
        role: [
            {"repo": result["repo"], **interval}
            for result in repo_results
            for interval in result["query_ranges"][role]
        ]
        for role in ROLE_FLAGS
    }
    pr_count = len(prs)

    approvals = sum(1 for r in reviews if r["review_state"] == "APPROVED")
    silent_approvals = sum(
        1
        for r in reviews
        if r["review_state"] == "APPROVED" and not r["body"].strip()
    )
    verdict_summary = {
        "prs_scanned": pr_count,
        "truncated_prs": truncated_prs,
        "reviews_collected": len(reviews),
        "states": counter_rows([r["review_state"] for r in reviews], "state"),
        "approvals": approvals,
        "silent_approvals": silent_approvals,
        "silent_approval_ratio": (
            round(silent_approvals / approvals, 3) if approvals else None
        ),
        "reviews_with_body": sum(1 for r in reviews if r["body"].strip()),
    }

    strongest_by_pr: dict[tuple[str, int], dict[str, Any]] = {}
    for comment in comments:
        if (
            not comment["path"]
            or not comment["body"].strip()
            or comment["ai_marked"]
        ):
            continue
        key = (comment["repo"], comment["pr_number"])
        current = strongest_by_pr.get(key)
        if current is None or comment["body_chars"] > current["body_chars"]:
            strongest_by_pr[key] = comment
    candidates = sorted(
        strongest_by_pr.values(),
        key=lambda comment: (-comment["body_chars"], comment["id"]),
    )[: args.candidate_limit]

    # Everything with words the person actually wrote feeds the learn loop:
    # inline review comments, their replies on their own PRs, conversation
    # comments, and review summary bodies. Silent reviews carry no text, so they
    # shape verdict_summary only.
    human_comments = [
        comment
        for comment in (comments + conversation_comments + reviews)
        if not comment["ai_marked"] and comment["body"].strip()
    ]
    comments_dir = args.comments_dir or args.output.parent / "comments"
    comment_batches = write_comment_batches(
        human_comments, comments_dir, args.batch_size
    )
    area_counts = counter_rows(
        [area_of(comment["repo"], comment["path"])
            for comment in human_comments
            if comment["path"]],
        "area",
    )
    kind_counts = counter_rows(
        [comment["kind"] for comment in human_comments], "kind"
    )
    author_side_counts = counter_rows(
        [
            "as_author" if comment["as_author"] else "as_reviewer"
            for comment in human_comments
        ],
        "side",
    )

    coverage_complete = all(
        interval["complete"]
        for intervals in query_ranges.values()
        for interval in intervals
    )
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repositories": args.repo,
        "requested_reviewer": args.login,
        "authenticated_login": authenticated_login,
        "coverage_complete": coverage_complete,
        "query_ranges": query_ranges,
        "counts": {
            "reviewed": len(indexed["reviewed"]),
            "commented": len(indexed["commented"]),
            "authored": len(indexed["authored"]),
            "unique_prs": pr_count,
            "inline_review_comments": len(comments),
            "conversation_comments": len(conversation_comments),
            "reviews_collected": len(reviews),
            "replies_on_own_prs": sum(
                1
                for comment in (comments + conversation_comments)
                if comment["as_author"] and comment["body"].strip()
            ),
            "prs_with_inline_review_comments": len(
                {(comment["repo"], comment["pr_number"]) for comment in comments}
            ),
            "excluded_ai_comments": sum(
                comment["ai_marked"]
                for comment in (comments + conversation_comments + reviews)
            ),
            "comments_with_links": sum(bool(comment["links"]) for comment in comments),
        },
        "created_range": value_range([entry["createdAt"] for entry in prs]),
        "updated_range": value_range([entry["updatedAt"] for entry in prs]),
        "states": counter_rows([entry["state"] for entry in prs], "state"),
        "authors": counter_rows([entry["author"] for entry in prs], "author"),
        "role_combinations": counter_rows(
            ["+".join(entry["roles"]) for entry in prs], "roles"
        ),
        "per_repo": [
            {
                "repo": repo,
                "unique_prs": len(result["prs"]),
                "human_comments": sum(
                    comment["repo"] == repo for comment in human_comments
                ),
            }
            for repo, result in zip(args.repo, repo_results)
        ],
        "prs": prs,
        "inline_review_comments": comments,
        "conversation_comments": conversation_comments,
        "reviews": reviews,
        "verdict_summary": verdict_summary,
        "area_counts": area_counts,
        "kind_counts": kind_counts,
        "author_side_counts": author_side_counts,
        "comment_batches": {
            "dir": str(comments_dir),
            "batch_size": args.batch_size,
            "human_comment_count": len(human_comments),
            "batch_count": len(comment_batches),
            "batches": comment_batches,
        },
        "candidate_selection": {
            "method": (
                "Longest non-Claude, non-empty, path-anchored inline comment per PR; "
                "a starting sample the main agent correlates to local code and git."
            ),
            "limit": args.candidate_limit,
            "candidates": candidates,
        },
        "collection_levels": {
            "pr_metadata_indexed": len(prs),
            "inline_comments_collected": len(comments),
            "conversation_comments_collected": len(conversation_comments),
            "reviews_collected": len(reviews),
            "human_comments_batched": len(human_comments),
            "comment_batches_written": len(comment_batches),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Index reviewed, commented, and authored PRs plus the person's inline "
            "comments, conversation replies (incl. on their own PRs), and review "
            "verdicts (approve / request-changes / comment, including silent ones). "
            "Handles GitHub Search's 1,000-result cap automatically."
        )
    )
    parser.add_argument(
        "--repo",
        action="append",
        required=True,
        help="Canonical owner/repository; repeat for several repositories",
    )
    parser.add_argument("--login", required=True, help="GitHub reviewer login")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Private run-scratch JSON output path",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help=(
            "Compact JSON for the agent to read; defaults to "
            "<output-stem>.summary.json"
        ),
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=30,
        help="Maximum deterministic candidate comments to include (default: 30)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=40,
        help="Human comments per batch file for iterative crunching (default: 40)",
    )
    parser.add_argument(
        "--comments-dir",
        type=Path,
        help="Directory for comment batch files (default: <output-dir>/comments)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.candidate_limit < 1:
        print("--candidate-limit must be positive.", file=sys.stderr)
        return 2
    if args.batch_size < 1:
        print("--batch-size must be positive.", file=sys.stderr)
        return 2
    try:
        result = collect(args)
        summary_output = args.summary_output or args.output.with_name(
            f"{args.output.stem}.summary.json"
        )
        summary = build_summary(result, args.output)
        atomic_write_json(args.output, result)
        atomic_write_json(summary_output, summary)
    except CollectionError as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        return 1

    counts = result["counts"]
    print(
        json.dumps(
            {
                "output": str(args.output),
                "summary_output": str(summary_output),
                "coverage_complete": result["coverage_complete"],
                "reviewed": counts["reviewed"],
                "commented": counts["commented"],
                "authored": counts["authored"],
                "unique_prs": counts["unique_prs"],
                "inline_review_comments": counts["inline_review_comments"],
                "conversation_comments": counts["conversation_comments"],
                "reviews_collected": counts["reviews_collected"],
                "replies_on_own_prs": counts["replies_on_own_prs"],
                "silent_approvals": result["verdict_summary"]["silent_approvals"],
                "silent_approval_ratio": result["verdict_summary"][
                    "silent_approval_ratio"
                ],
                "comments_with_links": counts["comments_with_links"],
                "comment_batches": result["comment_batches"]["batch_count"],
                "batch_dir": result["comment_batches"]["dir"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
