#!/usr/bin/env python3
"""Emit a structured completion signal at the end of a task episode.

Usage:
    python3 scripts/completion_signal.py \\
        --status delivered \\
        --target app/routes/strategies.py \\
        --boundary "Post-edit validation exits 0 and rename is committed" \\
        --summary "Commit cc497ad closes the singular-to-plural rename" \\
        --evidence commit:cc497ad \\
        --evidence validation:scripts/validate_changes.py

Required fields:
    --status       delivered | partial | deferred
    --target       What the episode changed or attempted to change.
    --boundary     The real acceptance boundary reached (or not).
    --summary      One-line reader-facing description of the result.

Optional fields:
    --episode-id   Stable identifier; auto-generated (timestamp+short uuid)
                   if omitted.
    --evidence     Repeatable. Reference to a commit, validation, PR, file,
                   or other bounded artifact that supports the claim.

The signal is appended as one JSON line to .claude/completion_log.jsonl
(relative to the repo root) so the agent's handoff has a durable,
auditable record of the acceptance boundary reached. The existing
handoff flow is untouched: this script writes one line and exits.

Exit codes:
    0   signal written
    1   validation error (bad status, missing required field)
    2   log path not writable
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / ".claude" / "completion_log.jsonl"

ALLOWED_STATUSES = ("delivered", "partial", "deferred")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--status", required=True, choices=ALLOWED_STATUSES)
    parser.add_argument("--target", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--episode-id", dest="episode_id", default=None)
    parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Repeatable evidence reference (commit:hash, validation:cmd, file:path, ...)",
    )
    return parser.parse_args(argv)


def short_id() -> str:
    """Generate a short, readable identifier from the wall clock + uuid."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:6]
    return f"{ts}-{suffix}"


def git_head(repo_root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def ensure_log_dir(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)


def build_record(args: argparse.Namespace, repo_root: Path) -> dict:
    record = {
        "episode_id": args.episode_id or short_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": args.status,
        "target": args.target,
        "acceptance_boundary": args.boundary,
        "summary": args.summary,
        "evidence": list(args.evidence),
        "schema_version": 1,
    }
    head = git_head(repo_root)
    if head:
        record["git_head"] = head
    return record


def append_record(log_path: Path, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main(argv: list[str]) -> int:
    args = parse_args(argv[1:])

    for field in ("target", "boundary", "summary"):
        value = getattr(args, field).strip()
        if not value:
            print(f"error: --{field.replace('_', '-')} must not be empty", file=sys.stderr)
            return 1

    try:
        ensure_log_dir(LOG_PATH)
        record = build_record(args, REPO_ROOT)
        append_record(LOG_PATH, record)
    except OSError as exc:
        print(f"error: could not write {LOG_PATH}: {exc}", file=sys.stderr)
        return 2

    print(
        f"completion_signal: status={record['status']} "
        f"episode_id={record['episode_id']} log={LOG_PATH.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))