#!/usr/bin/env python3
"""Run copy-council's deterministic evals.

Consistency cases call the model three times and pass when each seated
reviewer's scores stay within ±1. They are skipped cleanly when no model
is configured (COUNCIL_PROVIDER / COUNCIL_MODEL / API key).

Usage:
  python3 scripts/run_evals.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import calibrate  # noqa: E402
import council  # noqa: E402
import slop_gate  # noqa: E402

CASES = ROOT / "evals" / "cases.json"


def _fill(case: dict) -> str:
    if "fill" in case:
        return "x" * int(case["fill"])
    if "segments" in case:
        return "\n---\n".join("x" * int(n) for n in case["segments"])
    return case["rewrite"]


def _skill_weights() -> dict[str, dict]:
    text = (ROOT / "skills" / "council" / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith("| Type |") and "Dissenter" in line and "Cap" in line:
            start = index
            break
    if start is None:
        raise AssertionError("post-type weight table is missing from the council skill")
    parsed: dict[str, dict] = {}
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9:
            raise AssertionError(f"weight row has {len(cells)} cells: {line}")
        name = cells[0]
        weights = [float(cell) for cell in cells[1:7]]
        parsed[name] = {
            "weights": dict(zip(council.REVIEWERS, weights)),
            "dissenter": cells[7],
            "cap": None if cells[8] == "none" else int(cells[8]),
        }
    return parsed


def _prompt_case(case: dict) -> tuple[bool, str]:
    post_type = council.normalize_type(case["post_type"])
    prompt = council.build_prompt(
        case["post"],
        council.DEFAULT_VOICE,
        None,
        post_type,
    )
    missing = [item for item in case.get("contains", []) if item not in prompt]
    present = [item for item in case.get("absent", []) if item in prompt]
    if missing or present:
        return False, f"missing {missing}; present {present}"
    return True, ""


def _slop_case(original: str, rewrite: str, expect: str, flag_kind: str | None) -> tuple[bool, str]:
    result = slop_gate.check(original, rewrite)
    if expect == "pass":
        return result["ok"], "" if result["ok"] else json.dumps(result["flags"])
    if result["ok"]:
        return False, "expected the gate to flag the rewrite"
    if flag_kind and not any(flag["kind"] == flag_kind for flag in result["flags"]):
        return False, json.dumps(result["flags"])
    return True, ""


def run_case(case: dict) -> tuple[str, str]:
    """Return ('pass'|'fail'|'skip', detail)."""
    kind = case["check"]
    if kind == "output_format":
        result = council.analyze_output(case["output"], case["post_type"])
        errors = result["errors"]
        if case["expect"] == "pass":
            return ("pass", "") if not errors else ("fail", "; ".join(errors))
        if not errors:
            return "fail", "expected format errors"
        needle = case.get("error_contains")
        if needle and not any(needle in err for err in errors):
            return "fail", "; ".join(errors)
        return "pass", ""
    if kind == "char_limit":
        problems = council.char_limit_problems(_fill(case), case["post_type"])
        if case["expect"] == "pass":
            return ("pass", "") if not problems else ("fail", "; ".join(problems))
        return ("pass", "") if problems else ("fail", "expected a length failure")
    if kind == "slop":
        ok, detail = _slop_case(
            case["original"], case["rewrite"], case["expect"], case.get("flag_kind")
        )
        if not ok:
            return "fail", detail
        for extra in case.get("also", []):
            ok, detail = _slop_case(
                extra["original"], extra["rewrite"], case["expect"], case.get("flag_kind")
            )
            if not ok:
                return "fail", detail
        return "pass", ""
    if kind == "slop_example":
        data = json.loads((ROOT / "examples" / "ankit-10-tweets.json").read_text(encoding="utf-8"))
        post = data["posts"][case["index"]]
        if case["must_contain"] not in post["text"]:
            return "fail", "example post is not the one this case names"
        ok, detail = _slop_case(post["text"], post["rewrite"], case["expect"], case.get("flag_kind"))
        return ("pass", "") if ok else ("fail", detail)
    if kind == "score":
        post_type = council.normalize_type(case["post_type"]) if case.get("post_type") else None
        got = council.council_score(case["scores"], post_type)
        if got != case["expect_score"]:
            return "fail", f"score {got} != {case['expect_score']}"
        return "pass", ""
    if kind == "hooks":
        problem = council.hook_count_error(case["post"])
        if case["expect"] == "pass":
            return ("pass", "") if problem is None else ("fail", problem)
        return ("pass", "") if problem else ("fail", "expected a hook-count error")
    if kind == "prompt":
        ok, detail = _prompt_case(case)
        return ("pass", "") if ok else ("fail", detail)
    if kind == "skill_weights":
        parsed = _skill_weights()
        if set(parsed) != set(council.POST_TYPES):
            return "fail", f"types {sorted(parsed)} != {sorted(council.POST_TYPES)}"
        for name, spec in council.POST_TYPES.items():
            row = parsed[name]
            code_weights = {key: float(value) for key, value in spec["weights"].items()}
            if row["weights"] != code_weights or row["dissenter"] != spec["dissenter"]:
                return "fail", f"{name} table {row} != code"
            if row["cap"] != spec["char_cap"]:
                return "fail", f"{name} cap {row['cap']} != {spec['char_cap']}"
        return "pass", ""
    if kind == "report_legacy":
        markdown = council.render_report(str(ROOT / "examples" / "ankit-10-tweets.json"))
        payload = council.report_payload(str(ROOT / "examples" / "ankit-10-tweets.json"))
        if abs(payload["average_council_score"] - 52.2) > 1e-9:
            return "fail", f"average {payload['average_council_score']}"
        if "52.2/100" not in markdown:
            return "fail", "report markdown lost the 52.2 average"
        if "skills/council/voice/ankit.md" not in markdown:
            return "fail", "report still points at the old voice path"
        posts = json.loads((ROOT / "examples" / "ankit-10-tweets.json").read_text(encoding="utf-8"))["posts"]
        pareto = slop_gate.check(posts[4]["text"], posts[4]["rewrite"])
        limits = slop_gate.check(posts[6]["text"], posts[6]["rewrite"])
        if pareto["ok"] or not any(flag["kind"] == "number" and "20" in flag["match"] for flag in pareto["flags"]):
            return "fail", f"pareto rewrite gate {pareto}"
        if not limits["ok"]:
            return "fail", f"hyphen rewrite was flagged {limits}"
        return "pass", ""
    if kind == "calibration":
        if abs((calibrate.pearson([1, 2, 3], [1, 2, 3]) or 0) - 1) > 1e-9:
            return "fail", "pearson identity failed"
        if abs((calibrate.pearson([1, 2, 3], [3, 2, 1]) or 0) + 1) > 1e-9:
            return "fail", "pearson inverse failed"
        if calibrate.pearson([1, 1, 1], [1, 2, 3]) is not None:
            return "fail", "pearson should be undefined when a side is constant"
        report = calibrate.build_report(
            calibrate.load_rows(ROOT / "calibration" / "example-posts.csv"),
            "calibration/example-posts.csv",
        )
        for phrase in (
            "EXAMPLE_NOT_REAL",
            "not a published result",
            "correlation is not defined",
        ):
            if phrase not in report:
                return "fail", f"report missing {phrase!r}"
        return "pass", ""
    if kind == "consistency":
        ok, reason = council.model_status()
        if not ok:
            return "skip", reason
        post_type = council.normalize_type(case["post_type"])
        active = council.seated(post_type)
        collected: dict[str, list[int]] = {name: [] for name in active}
        runs = int(case.get("runs", 3))
        tolerance = int(case.get("tolerance", 1))
        for index in range(runs):
            prompt = council.build_prompt(case["post"], council.DEFAULT_VOICE, None, post_type)
            raw = council.call_llm(prompt)
            analysis = council.analyze_output(raw, post_type)
            if not analysis["parse_ok"]:
                return "fail", f"run {index + 1} did not parse: {analysis['errors']}"
            for name in active:
                collected[name].append(analysis["scores"][name])
        drifted = {
            name: values
            for name, values in collected.items()
            if max(values) - min(values) > tolerance
        }
        if drifted:
            return "fail", f"scores moved by more than {tolerance}: {drifted}"
        return "pass", json.dumps(collected)
    return "fail", f"unknown check {kind}"


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def cli_smokes() -> list[tuple[str, str, str]]:
    """Small process-level checks. Not counted in the 20-30 cases."""
    results = []
    prompt = _cli(
        "scripts/council.py",
        "prompt",
        "Ship the draft today.",
        "--type",
        "one-liner",
        "--json",
        "--no-log",
    )
    try:
        payload = json.loads(prompt.stdout)
        ok = prompt.returncode == 0 and payload["version"] == "1.0.0" and "kaam karo na" in payload["prompt"]
        detail = "" if ok else prompt.stderr or prompt.stdout[:400]
    except json.JSONDecodeError:
        ok = False
        detail = prompt.stdout[:400]
    results.append(("cli-prompt-json", "pass" if ok else "fail", detail))

    short = _cli(
        "scripts/council.py",
        "prompt",
        "--type",
        "reel-hook",
        "--file",
        str(ROOT / "evals" / "two-hooks.txt"),
        "--no-log",
    )
    ok = short.returncode == 2 and "3 to 6" in short.stderr
    results.append(("cli-reel-hook-count", "pass" if ok else "fail", short.stderr.strip() or short.stdout[:200]))

    clean = _cli(
        "scripts/slop_gate.py",
        "--original",
        "limits- kaam karo na",
        "--rewrite",
        "Hitting the limit isn't a flex- kaam karo na.",
    )
    dirty = _cli(
        "scripts/slop_gate.py",
        "--original",
        "Ship the draft.",
        "--rewrite",
        "Let us delve into the draft.",
    )
    ok = clean.returncode == 0 and dirty.returncode == 1
    results.append(("cli-slop-gate", "pass" if ok else "fail", f"clean {clean.returncode} dirty {dirty.returncode}"))

    report = _cli("scripts/calibrate.py", "calibration/example-posts.csv")
    ok = report.returncode == 0 and "EXAMPLE_NOT_REAL" in report.stdout and "correlation is not defined" in report.stdout
    results.append(("cli-calibrate", "pass" if ok else "fail", report.stderr[:200] or report.stdout[:200]))
    return results


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if not 20 <= len(cases) <= 30:
        print(f"expected 20 to 30 cases, found {len(cases)}")
        sys.exit(1)
    failed = 0
    skipped = 0
    for case in cases:
        status, detail = run_case(case)
        if status == "fail":
            failed += 1
        elif status == "skip":
            skipped += 1
        line = f"{status.upper():4} {case['id']}"
        if detail and status != "pass":
            line += f" — {detail}"
        print(line)
    print()
    smokes = cli_smokes()
    for name, status, detail in smokes:
        if status == "fail":
            failed += 1
        line = f"{status.upper():4} {name}"
        if detail and status != "pass":
            line += f" — {detail}"
        print(line)
    smoke_fails = sum(1 for _, status, _ in smokes if status == "fail")
    case_fails = failed - smoke_fails
    print()
    print(
        f"{len(cases) - case_fails - skipped} passed, {skipped} skipped, {case_fails} failed"
        f" ({len(cases)} cases); cli smokes failed: {smoke_fails}"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
