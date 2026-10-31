#!/usr/bin/env python3
"""Deterministic anti-slop and fact gate for a rewrite.

Flags banned AI-style words and contrast patterns, and any digit number in
the rewrite that is not in the original. The author's hyphen-dash (ASCII
hyphen-minus, including "limits- kaam") is allowed and is not a pattern.

The pattern idea is adapted from blader/humanizer (Siqi Chen, MIT). This
file is a small subset written for copy-council, not a copy of that skill.
See NOTICE.md.

Usage:
  python3 scripts/slop_gate.py --original "post" --rewrite "rewrite"
  python3 scripts/slop_gate.py --original-file a.txt --rewrite-file b.txt --json

Exit 0 when the rewrite is clean, 1 when it is flagged.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Whole words only. Hyphenated forms that are themselves AI tells are listed
# in full ("cutting-edge"); a plain hyphen-minus is never banned.
BANNED_WORDS = (
    "delve",
    "delves",
    "delving",
    "tapestry",
    "testament",
    "pivotal",
    "showcase",
    "showcases",
    "showcasing",
    "underscore",
    "underscores",
    "underscoring",
    "leverage",
    "leverages",
    "leveraging",
    "synergy",
    "synergies",
    "empower",
    "empowers",
    "empowering",
    "seamless",
    "elevate",
    "elevates",
    "elevating",
    "multifaceted",
    "holistic",
    "paradigm",
    "utilize",
    "utilizes",
    "utilizing",
    "nestled",
    "game-changer",
    "gamechanger",
    "cutting-edge",
)

BANNED_PHRASES = (
    "at its core",
    "here's the thing",
    "here’s the thing",
    "let that sink in",
    "let's dive in",
    "let’s dive in",
    "in today's world",
    "in today’s world",
    "in today's fast-paced",
    "in today’s fast-paced",
)

# "It's not X, it's Y" and the close variants. Both sides are required, so
# "isn't a flex" with no following "it's ..." is not a match.
_APOS = r"['’]"
_IT_IS = rf"it(?:{_APOS}s| is)"
CONTRAST_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "It's not X, it's Y",
        re.compile(rf"\b{_IT_IS}\s+not\b[^.!?\n]{{0,120}}?\b{_IT_IS}\b", re.I),
    ),
    (
        "This isn't X, it's Y",
        re.compile(
            rf"\bthis\s+(?:isn{_APOS}t|is not)\b[^.!?\n]{{0,120}}?\b{_IT_IS}\b",
            re.I,
        ),
    ),
    (
        "not just X, but Y",
        re.compile(rf"\bnot just\b[^.!?\n]{{0,120}}?\b(?:but|{_IT_IS})\b", re.I),
    ),
    (
        "not because X, because Y",
        re.compile(r"\bnot because\b[^.!?\n]{0,120}?\bbecause\b", re.I),
    ),
)

_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?%?")


def _canon_number(token: str) -> set[str]:
    """Forms of a numeric token that count as 'the same number'."""
    body = token.replace(",", "").replace("%", "")
    forms = {body}
    if re.fullmatch(r"\d+\.0+", body):
        forms.add(body.split(".", 1)[0])
    return forms


def number_forms(text: str) -> set[str]:
    forms: set[str] = set()
    for match in _NUMBER.findall(text):
        forms |= _canon_number(match)
    return forms


def check(original: str, rewrite: str) -> dict:
    """Return {"ok": bool, "flags": [{"kind", "match", "detail"}, ...]}."""
    flags: list[dict] = []
    haystack = rewrite.lower()

    for word in BANNED_WORDS:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", haystack):
            flags.append(
                {
                    "kind": "banned_word",
                    "match": word,
                    "detail": f"banned word {word!r} in the rewrite",
                }
            )

    for phrase in BANNED_PHRASES:
        if phrase.lower() in haystack:
            flags.append(
                {
                    "kind": "banned_phrase",
                    "match": phrase,
                    "detail": f"banned phrase {phrase!r} in the rewrite",
                }
            )

    for name, pattern in CONTRAST_PATTERNS:
        found = pattern.search(rewrite)
        if found:
            flags.append(
                {
                    "kind": "pattern",
                    "match": name,
                    "detail": found.group(0).strip(),
                }
            )

    original_numbers = number_forms(original)
    for token in _NUMBER.findall(rewrite):
        forms = _canon_number(token)
        if forms.isdisjoint(original_numbers):
            flags.append(
                {
                    "kind": "number",
                    "match": token,
                    "detail": "number in the rewrite is not in the original",
                }
            )

    return {"ok": not flags, "flags": flags}


def _read_arg(value: str | None, file_path: str | None, label: str) -> str:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if value is None:
        sys.exit(f"Give --{label} or --{label}-file")
    return value


def main() -> None:
    ap = argparse.ArgumentParser(description="Flag slop and new numbers in a rewrite")
    ap.add_argument("--original")
    ap.add_argument("--original-file")
    ap.add_argument("--rewrite")
    ap.add_argument("--rewrite-file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    original = _read_arg(args.original, args.original_file, "original")
    rewrite = _read_arg(args.rewrite, args.rewrite_file, "rewrite")
    result = check(original, rewrite)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["ok"]:
        print("SLOP GATE: pass")
    else:
        print("SLOP GATE: fail")
        for flag in result["flags"]:
            print(f"- {flag['kind']}: {flag['match']} ({flag['detail']})")
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
