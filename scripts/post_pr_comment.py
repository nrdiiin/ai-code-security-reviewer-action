#!/usr/bin/env python3
"""Post or update a PR comment with scan results using GitHub REST API."""

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MARKER = "<!-- aicsr-scan-comment -->"
API_BASE = "https://api.github.com"


def github_api(method: str, url: str, token: str, data: dict | None = None) -> dict | list:
    """Make a GitHub REST API call."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    if body:
        req.add_header("Content-Type", "application/json")

    with urlopen(req) as resp:
        if resp.status == 204:
            return {}
        return json.loads(resp.read().decode())


def find_existing_comment(repo: str, pr_number: int, token: str) -> int | None:
    """Find an existing bot comment with our marker. Returns comment ID or None."""
    url = f"{API_BASE}/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    try:
        comments = github_api("GET", url, token)
    except HTTPError as e:
        print(f"Warning: Could not fetch comments: {e}")
        return None

    for comment in comments:
        if MARKER in comment.get("body", ""):
            return comment["id"]
    return None


def post_comment(repo: str, pr_number: int, token: str, body: str) -> None:
    """Create a new PR comment."""
    url = f"{API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    github_api("POST", url, token, {"body": body})
    print(f"Posted new comment on PR #{pr_number}")


def update_comment(repo: str, comment_id: int, token: str, body: str) -> None:
    """Update an existing comment."""
    url = f"{API_BASE}/repos/{repo}/issues/comments/{comment_id}"
    github_api("PATCH", url, token, {"body": body})
    print(f"Updated existing comment #{comment_id}")


def main():
    parser = argparse.ArgumentParser(description="Post or update PR comment")
    parser.add_argument("--token", required=True, help="GitHub token")
    parser.add_argument("--comment-file", required=True, help="Path to markdown comment file")
    parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    parser.add_argument("--event", required=True, help="GitHub event name")
    parser.add_argument("--pr-number", type=str, default="", help="PR number")
    args = parser.parse_args()

    # Only post comments on pull_request events
    if args.event != "pull_request":
        print(f"Event is '{args.event}', not 'pull_request'. Skipping PR comment.")
        return

    # Convert pr-number to int after event check (avoids crash on empty string)
    try:
        pr_number = int(args.pr_number)
    except (ValueError, TypeError):
        print(f"Invalid PR number '{args.pr_number}'. Skipping PR comment.")
        return

    if pr_number <= 0:
        print("No valid PR number found. Skipping PR comment.")
        return

    # Read comment body
    if not os.path.exists(args.comment_file):
        print(f"Comment file {args.comment_file} not found. Skipping.")
        return

    body = Path(args.comment_file).read_text()
    if not body.strip():
        print("Comment file is empty. Skipping.")
        return

    # Find existing comment or create new one
    existing_id = find_existing_comment(args.repo, pr_number, args.token)
    if existing_id:
        update_comment(args.repo, existing_id, args.token, body)
    else:
        post_comment(args.repo, pr_number, args.token, body)


if __name__ == "__main__":
    main()
