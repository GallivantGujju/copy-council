#!/usr/bin/env python3
"""Score a CSV of posts against public X metrics and write a correlation report.

The CSV needs a header. Required column: post_text.
Metric columns, any subset: impressions, likes, reposts, replies, bookmarks, quotes.
Optional: post_type, council_score, label, url, notes.

Rows that already have council_score are used as given. Empty scores are filled
by a council run when a model is configured. With no model, those rows are
left unscored and the report says scoring was skipped.

The correlation is Pearson r. It is not defined when a column does not vary.
This script does not invent metrics. calibration/example-posts.csv is a
labelled fixture, not a measurement.

Usage:
  python3 scripts/calibrate.py calibration/example-posts.csv
  python3 scripts/calibrate.py posts.csv --out calibration/out/report.md
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import council  # noqa: E402

METRICS = ("impressions", "likes", "reposts", "replies", "bookmarks", "quotes")
ROOT = SCRIPTS.parent


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson r, or None when either side does not vary or n < 2."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _blank(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def score_row(row: dict) -> tuple[float | None, str | None]:
    """Return (score, skip_reason). skip_reason is set when a model is required and absent."""
    raw = row.get("council_score", "")
    if not _blank(raw):
        return float(raw), None
    ok, reason = council.model_status()
    if not ok:
        return None, reason
    post_type = council.normalize_type(row.get("post_type") or "")
    prompt = council.build_prompt(row["post_text"], council.DEFAULT_VOICE, None, post_type)
    raw_reply = council.call_llm(prompt)
    analysis = council.analyze_output(raw_reply, post_type)
    if not analysis.get("parse_ok"):
        return None, "council reply did not parse"
    score = analysis.get("expected_score")
    if score is None:
        score = analysis.get("council_score")
    if score is None:
        return None, "council reply had no score"
    return float(score), None


def build_report(rows: list[dict], source: str) -> str:
    lines = [
        "# Council score and public metrics",
        "",
        f"Source: {source}",
        f"Rows: {len(rows)}",
        "",
    ]
    labels = {(row.get("label") or "").strip() for row in rows}
    if "EXAMPLE_NOT_REAL" in labels:
        lines += [
            "These rows are labelled EXAMPLE_NOT_REAL. They are not measurements and are not a published result.",
            "",
        ]
    if not rows:
        lines.append("No rows, so correlation is not defined.")
        return "\n".join(lines) + "\n"

    scored: list[tuple[dict, float]] = []
    skipped = 0
    skip_reason = None
    for row in rows:
        if "post_text" not in row:
            raise ValueError("CSV needs a post_text column")
        value, reason = score_row(row)
        if value is None:
            skipped += 1
            skip_reason = reason
            continue
        scored.append((row, value))
    if skipped:
        lines.append(
            f"Scoring skipped for {skipped} row(s): {skip_reason or 'no score'}."
        )
        lines.append("")
    if len(scored) < 2:
        lines.append("Fewer than two scored rows, so correlation is not defined.")
        return "\n".join(lines) + "\n"

    lines.append("| # | council_score | post |")
    lines.append("|---|---|---|")
    for index, (row, value) in enumerate(scored, 1):
        snippet = " ".join(row["post_text"].split())
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        lines.append(f"| {index} | {value:g} | {snippet} |")
    lines.append("")
    lines.append("## Correlation")
    lines.append("")
    any_metric = False
    for metric in METRICS:
        pairs: list[tuple[float, float]] = []
        for row, value in scored:
            raw = row.get(metric, "")
            if _blank(raw):
                continue
            pairs.append((value, float(raw)))
        if len(pairs) < 2:
            continue
        any_metric = True
        coefficient = pearson([item[0] for item in pairs], [item[1] for item in pairs])
        if coefficient is None:
            lines.append(
                f"- {metric}: correlation is not defined because the values do not vary (n={len(pairs)})."
            )
        else:
            lines.append(f"- {metric}: Pearson r = {coefficient:.3f} (n={len(pairs)}).")
    if not any_metric:
        lines.append("No metric column with two values, so correlation is not defined.")
    lines.append("")
    lines.append(
        "Pearson r describes this file only. A house rubric is not a prediction of engagement."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Correlate council scores with public X metrics")
    ap.add_argument("csv_path")
    ap.add_argument("--out", help="write the markdown report here as well as stdout")
    args = ap.parse_args()
    path = Path(args.csv_path)
    if not path.is_file():
        sys.exit(f"CSV not found: {path}")
    report = build_report(load_rows(path), str(path))
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
