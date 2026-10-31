#!/usr/bin/env python3
"""Fail when a markdown link or a repo path points at a file that is not there.

Checks, from the repo root:

- Relative links in markdown, resolved from the file and from the repo root.
- Backtick paths that start with a known directory, or `voice/...` next to a skill.
- Quoted paths in Python and markdown that start with a known directory.

Generated output under `runs/` is not required to exist. Angle-bracket
placeholders such as `<name>` are skipped.

Usage:
  python3 scripts/check_links.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "runs", ".cursor"}
KNOWN = ("skills/", "scripts/", "evals/", "calibration/", "examples/", "voice/", ".github/")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
QUOTED_RE = re.compile(
    r"""['"]((?:skills|scripts|evals|calibration|examples|voice|\.github)/[A-Za-z0-9_./-]+)['"]"""
)
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".txt"}


def _concrete(raw: str) -> str | None:
    text = raw.strip().strip("<>")
    if not text or any(char in text for char in "<>*|{}"):
        return None
    if "..." in text:
        return None
    text = text.split("#", 1)[0].strip()
    text = text.split()[0] if text.split() else text
    if text.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if text.startswith("runs/"):
        return None
    return text or None


def _exists(candidates: list[Path]) -> bool:
    return any(path.is_file() or path.is_dir() for path in candidates)


def _should_walk(path: Path) -> bool:
    return path.is_file() and path.suffix in TEXT_SUFFIXES and not any(
        part in SKIP_DIRS for part in path.relative_to(ROOT).parts
    )


def missing_refs() -> list[str]:
    problems: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not _should_walk(path):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        seen: set[str] = set()

        def check(raw: str, where: str) -> None:
            concrete = _concrete(raw)
            if concrete is None or concrete in seen:
                return
            looks_known = concrete.startswith(KNOWN) or concrete.startswith("voice/")
            looks_link = where == "link" and ("/" in concrete or "." in Path(concrete).name)
            if not looks_known and not looks_link:
                return
            seen.add(concrete)
            candidates = [ROOT / concrete, path.parent / concrete]
            if _exists(candidates):
                return
            problems.append(f"{rel}: {where} {concrete} is not a file")

        for match in LINK_RE.finditer(text):
            check(match.group(1), "link")
        for match in TICK_RE.finditer(text):
            check(match.group(1), "path")
        for match in QUOTED_RE.finditer(text):
            check(match.group(1), "path")
    return problems


def main() -> None:
    problems = missing_refs()
    if problems:
        print(f"link check: {len(problems)} missing")
        for item in problems:
            print(f"- {item}")
        sys.exit(1)
    print("link check: ok")


if __name__ == "__main__":
    main()
