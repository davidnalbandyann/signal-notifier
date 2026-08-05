#!/usr/bin/env python3
"""Run the smallest project-owned check that covers each changed file.

Usage:
    python3 scripts/validate_changes.py <file> [<file> ...]

Maps a file path to one focused check based on extension, then exits
non-zero if any check fails. Designed to be called by an agent (or a
human) after the last material edit, before handoff.

The mapping is intentionally minimal: prefer syntax/type checks over
running full test suites so the feedback loop stays fast. Pull in the
full test suite separately when the change touches test files or when
the agent wants broader coverage.

Recognised extensions and their checks:

    *.py            python3 -m py_compile <file>
    *.ts, *.tsx,
    *.vue, *.js,
    *.jsx           npx vue-tsc --noEmit     (run from frontend/)

Files outside the project tree, files that do not exist, and files with
unrecognised extensions are skipped with a warning so the script never
blocks on inputs it cannot evaluate.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

PY_EXTS = {".py"}
TS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".vue"}


def classify(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in PY_EXTS:
        return "py"
    if ext in TS_EXTS:
        return "ts"
    return None


def run_py(repo_root: Path, files: list[Path]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(f.relative_to(repo_root)) for f in files]],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def run_ts(frontend_dir: Path, _files: list[Path]) -> tuple[int, str]:
    if not (frontend_dir / "node_modules").exists():
        return 0, "skipped (frontend/node_modules missing)"
    proc = subprocess.run(
        ["npx", "--no-install", "vue-tsc", "--noEmit"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_changes.py <file> [<file> ...]", file=sys.stderr)
        return 2

    py_files: list[Path] = []
    ts_files: list[Path] = []
    skipped: list[tuple[Path, str]] = []

    for raw in argv[1:]:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / raw).resolve()
        if not path.exists():
            skipped.append((path, "missing on disk"))
            continue
        kind = classify(path)
        if kind == "py":
            py_files.append(path)
        elif kind == "ts":
            ts_files.append(path)
        else:
            skipped.append((path, "unrecognised extension"))

    failed = False

    if py_files:
        rc, out = run_py(REPO_ROOT, py_files)
        print(f"[py]   {len(py_files)} file(s) -> rc={rc}")
        if out:
            print(out)
        if rc != 0:
            failed = True

    if ts_files:
        rc, out = run_ts(FRONTEND_DIR, ts_files)
        print(f"[ts]   {len(ts_files)} file(s) -> rc={rc}")
        if out:
            print(out)
        if rc != 0:
            failed = True

    for path, reason in skipped:
        print(f"[skip] {path} ({reason})")

    if failed:
        print("validate_changes: FAIL", file=sys.stderr)
        return 1
    print("validate_changes: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))