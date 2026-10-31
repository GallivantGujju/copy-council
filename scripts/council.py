#!/usr/bin/env python3
"""copy-council CLI.

Build the council prompt for a post, optionally send it to an LLM, or render
a results JSON file into a markdown report. Standard library only.

Usage:
  python3 scripts/council.py prompt "your post" [--type one-liner] [--json]
  python3 scripts/council.py run "your post" --type one-liner
  python3 scripts/council.py report examples/ankit-10-tweets.json
  python3 scripts/council.py prompt --type reel-hook --file hooks.txt --json

Post types: one-liner, quote-post, thread, ad (ad/landing copy), reel-hook.
Omit --type to seat all six reviewers at weight 1 (the unweighted average).

Reel-hook mode seats Ogilvy, Sugarman and Schwartz only and expects 3 to 6
hooks, one per line, or separated by a line that is only ---.

Env vars for `run` are unchanged: COUNCIL_PROVIDER, COUNCIL_MODEL, the
provider API key, COUNCIL_BASE_URL, COUNCIL_API_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import slop_gate  # noqa: E402

ROOT = SCRIPTS.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DEFAULT_VOICE = "skills/council/voice/ankit.md"
DEFAULT_LOG = ROOT / "runs" / "council.jsonl"
REVIEWERS = ["ogilvy", "halbert", "schwartz", "sugarman", "hopkins", "cialdini"]
REVIEWER_TITLES = {
    "ogilvy": "Ogilvy",
    "halbert": "Halbert",
    "schwartz": "Schwartz",
    "sugarman": "Sugarman",
    "hopkins": "Hopkins",
    "cialdini": "Cialdini",
}
SIMULATION_LINE = (
    "SIMULATED COUNCIL: paraphrased principles, not a review by these people."
)

# House weights, not fitted to engagement. 0 means the reviewer is not seated
# and does not enter the average. Documented again in skills/council/SKILL.md.
POST_TYPES: dict[str, dict] = {
    "one-liner": {
        "label": "one-liner",
        "weights": {
            "ogilvy": 1,
            "halbert": 1,
            "schwartz": 1,
            "sugarman": 1,
            "hopkins": 0,
            "cialdini": 0.5,
        },
        "dissenter": "schwartz",
        "char_cap": 280,
        "skip_reasons": {
            "hopkins": (
                "A one-line opinion cannot carry proof, so Hopkins does not enter the average."
            ),
        },
    },
    "quote-post": {
        "label": "quote-post",
        "weights": {
            "ogilvy": 1.5,
            "halbert": 1,
            "schwartz": 1,
            "sugarman": 1,
            "hopkins": 0.5,
            "cialdini": 1,
        },
        "dissenter": "ogilvy",
        "char_cap": 280,
        "skip_reasons": {},
    },
    "thread": {
        "label": "thread",
        "weights": {
            "ogilvy": 1,
            "halbert": 1,
            "schwartz": 1,
            "sugarman": 1.5,
            "hopkins": 1,
            "cialdini": 1,
        },
        "dissenter": "hopkins",
        "char_cap": 280,
        "skip_reasons": {},
    },
    "ad": {
        "label": "ad/landing copy",
        "weights": {
            "ogilvy": 1.5,
            "halbert": 1,
            "schwartz": 1,
            "sugarman": 1,
            "hopkins": 1.5,
            "cialdini": 1,
        },
        "dissenter": "halbert",
        "char_cap": None,
        "skip_reasons": {},
    },
    "reel-hook": {
        "label": "reel hook",
        "weights": {
            "ogilvy": 1,
            "halbert": 0,
            "schwartz": 1,
            "sugarman": 1,
            "hopkins": 0,
            "cialdini": 0,
        },
        "dissenter": "schwartz",
        "char_cap": None,
        "skip_reasons": {
            "halbert": "Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.",
            "hopkins": "Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.",
            "cialdini": "Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.",
        },
    },
}

UNSPECIFIED: dict = {
    "label": "unspecified",
    "weights": {name: 1 for name in REVIEWERS},
    "dissenter": "hopkins",
    "char_cap": 280,
    "skip_reasons": {},
}

TYPE_ALIASES = {
    "one-liner": "one-liner",
    "oneliner": "one-liner",
    "one liner": "one-liner",
    "quote-post": "quote-post",
    "quote": "quote-post",
    "quotepost": "quote-post",
    "thread": "thread",
    "ad": "ad",
    "landing": "ad",
    "ad/landing": "ad",
    "ad-landing": "ad",
    "landing-copy": "ad",
    "reel-hook": "reel-hook",
    "reel": "reel-hook",
    "reel hook": "reel-hook",
    "hooks": "reel-hook",
}

_REVIEWER_LINE = re.compile(
    r"^  (Ogilvy|Halbert|Schwartz|Sugarman|Hopkins|Cialdini)[ \t]+(\S+)[ \t]*(.*)$"
)
_HOOK_HEAD = re.compile(r"^HOOK\s+(\d+)\s*:\s*$", re.I)
_BEST_HOOK = re.compile(r"^BEST HOOK:\s*(\d+)\s*$", re.I)


def normalize_type(raw: str | None) -> str | None:
    """Return a canonical post type, or None when the run is untyped.

    None seats every reviewer at weight 1. An unknown name raises ValueError.
    """
    if raw is None or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    if key in ("unspecified", "all"):
        return None
    if key not in TYPE_ALIASES:
        known = ", ".join(POST_TYPES)
        raise ValueError(f"Unknown post type {raw!r}. Known: {known}")
    return TYPE_ALIASES[key]


def spec_for(post_type: str | None) -> dict:
    if post_type is None:
        return UNSPECIFIED
    return POST_TYPES[post_type]


def seated(post_type: str | None) -> list[str]:
    weights = spec_for(post_type)["weights"]
    return [name for name in REVIEWERS if weights[name] > 0]


def council_score(scores: dict, post_type: str | None = None) -> int:
    """Weighted mean of seated reviewers, times 10, Python round.

    Halves round to the nearest even integer, which is Python's round.
    Reviewers with weight 0 are ignored, so a low Hopkins score cannot
    move a one-liner.
    """
    weights = spec_for(post_type)["weights"]
    active = [name for name in REVIEWERS if weights[name] > 0]
    missing = [name for name in active if name not in scores]
    if missing:
        raise KeyError(f"missing scores for {', '.join(missing)}")
    total_w = sum(weights[name] for name in active)
    mean = sum(scores[name] * weights[name] for name in active) / total_w
    return round(mean * 10)


def split_hooks(text: str) -> list[str]:
    """Split a hook list. A line that is only --- separates hooks.

    Without that separator, each non-empty line is one hook.
    """
    stripped = text.strip()
    if re.search(r"(?m)^---\s*$", stripped):
        parts = re.split(r"(?m)^---\s*$", stripped)
    else:
        parts = stripped.splitlines()
    return [part.strip() for part in parts if part.strip()]


def hook_count_error(text: str) -> str | None:
    count = len(split_hooks(text))
    if 3 <= count <= 6:
        return None
    return f"reel-hook mode needs 3 to 6 hooks, found {count}"


def rewrite_segments(rewrite: str, post_type: str | None) -> list[str]:
    if post_type == "thread":
        parts = re.split(r"(?m)^---\s*$", rewrite.strip())
        return [part.strip() for part in parts if part.strip()]
    body = rewrite.strip()
    return [body] if body else []


def char_limit_problems(rewrite: str, post_type: str | None) -> list[str]:
    """Raw character counts. X post types are capped at 280 per post.

    Ad/landing copy and reel hooks have no 280 cap. A thread is capped
    per post, split on a line that is only ---.
    """
    cap = spec_for(post_type)["char_cap"]
    if not cap:
        return []
    problems = []
    for index, segment in enumerate(rewrite_segments(rewrite, post_type), 1):
        if len(segment) > cap:
            label = f"post {index}" if post_type == "thread" else "rewrite"
            problems.append(f"{label} is {len(segment)} characters (cap {cap})")
    return problems


def read_skill(name: str) -> str:
    path = ROOT / "skills" / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text.strip()


def _weight_phrase(post_type: str | None) -> str:
    spec = spec_for(post_type)
    parts = []
    for name in REVIEWERS:
        weight = spec["weights"][name]
        if weight == 0:
            reason = spec["skip_reasons"].get(name, "not seated for this post type")
            parts.append(f"- {name}: skipped. {reason}")
        else:
            mark = " (designated dissenter)" if name == spec["dissenter"] else ""
            parts.append(f"- {name}: weight {weight:g}{mark}")
    return "\n".join(parts)


def output_template(post_type: str | None) -> str:
    spec = spec_for(post_type)
    rows = []
    for name in REVIEWERS:
        title = REVIEWER_TITLES[name]
        if spec["weights"][name] == 0:
            reason = spec["skip_reasons"].get(name, "not seated for this post type")
            rows.append(f"  {title:<8} skipped  {reason}")
            continue
        extra = ""
        if name == "schwartz":
            extra = "  (awareness: <level>)"
        if name == spec["dissenter"]:
            extra += " [dissenter]"
        rows.append(f"  {title:<8} <0-10>/10  <one-line reason>{extra}")
    body = "\n".join(
        [
            "COUNCIL: <weighted score>/100",
            *rows,
            "TOP FIX: <one sentence>",
            "REWRITE:",
            "<text>",
        ]
    )
    if post_type == "reel-hook":
        return "\n".join(
            [
                SIMULATION_LINE,
                "POST TYPE: reel hook",
                "Then one block per hook, in order. Do not repeat the simulation line inside a hook.",
                "",
                "HOOK <n>:",
                body,
                "",
                "After the last hook, one line: BEST HOOK: <n>",
                "BEST HOOK is the highest council score. Ties go to the earlier hook.",
            ]
        )
    return "\n".join([SIMULATION_LINE, f"POST TYPE: {spec['label']}", body])


def build_prompt(post: str, voice_path: str | None, context: str | None, post_type: str | None) -> str:
    spec = spec_for(post_type)
    cap = spec["char_cap"]
    cap_line = (
        f"Each X post in the rewrite is at most {cap} characters (raw character count, not X's shortened-URL count)."
        if cap
        else "This post type has no 280-character cap."
    )
    if post_type == "thread":
        cap_line += " Separate thread posts with a line that is only ---."
    parts = [
        "You are the copy council. Follow the orchestrator instructions exactly.",
        "## Orchestrator\n" + read_skill("council"),
        "## This run\n"
        + "\n".join(
            [
                f"Post type: {spec['label']}.",
                "Weights for this run (house weights, not fitted to engagement):",
                _weight_phrase(post_type),
                f"Designated dissenter: {spec['dissenter']}. Their reason ends with the marker [dissenter] and states the strongest case against the post.",
                cap_line,
                "Exactly one TOP FIX line. One fix, not a list.",
                "Do not invent facts, numbers, names, or stories. Use [fact needed] when something is missing.",
                "Do not write an It's not X, it's Y contrast. Keep the author's hyphen-dash if they use one.",
                "Start the reply with this exact line:",
                SIMULATION_LINE,
                "",
                "Output format:",
                output_template(post_type),
            ]
        ),
    ]
    for name in seated(post_type):
        parts.append(f"## Reviewer: {name}\n" + read_skill(name))
    if voice_path:
        vp = Path(voice_path)
        if not vp.is_absolute():
            vp = ROOT / vp
        if not vp.is_file():
            raise FileNotFoundError(f"Voice file not found: {vp}")
        parts.append("## Author voice profile\n" + vp.read_text(encoding="utf-8").strip())
    if context:
        parts.append("## Context\n" + context.strip())
    if post_type == "reel-hook":
        hooks = split_hooks(post)
        body = "\n\n".join(f"### Hook {index}\n{hook}" for index, hook in enumerate(hooks, 1))
        parts.append("## Hooks to score\n" + body)
    else:
        parts.append("## Post to review\n```\n" + post.strip() + "\n```")
    parts.append(
        "Return only the output format above. "
        "Score only the seated reviewers. "
        "Do not invent facts."
    )
    return "\n\n".join(parts)


def _post_json(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def model_status() -> tuple[bool, str]:
    """Whether `run` can call a model. A false status is a clean skip, not a crash."""
    provider = os.environ.get("COUNCIL_PROVIDER", "none").lower()
    model = os.environ.get("COUNCIL_MODEL", "").strip()
    if provider in ("", "none"):
        return False, "COUNCIL_PROVIDER is unset or none"
    if not model:
        return False, "COUNCIL_MODEL is unset"
    needed = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "xai": "XAI_API_KEY",
    }
    if provider in needed and not os.environ.get(needed[provider]):
        return False, f"{needed[provider]} is unset"
    if provider == "openai-compatible" and not os.environ.get("COUNCIL_BASE_URL"):
        return False, "COUNCIL_BASE_URL is unset"
    if provider not in ("anthropic", "openai", "xai", "openai-compatible"):
        return False, f"unknown COUNCIL_PROVIDER {provider}"
    return True, provider


def call_llm(prompt: str) -> str:
    provider = os.environ.get("COUNCIL_PROVIDER", "none").lower()
    model = os.environ.get("COUNCIL_MODEL")
    if not model:
        sys.exit("Set COUNCIL_MODEL for the chosen provider.")
    msgs = [{"role": "user", "content": prompt}]
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY") or sys.exit("Set ANTHROPIC_API_KEY")
        out = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": 2000, "messages": msgs},
        )
        return "".join(block.get("text", "") for block in out.get("content", []))
    if provider in ("openai", "xai", "openai-compatible"):
        base = {
            "openai": "https://api.openai.com/v1",
            "xai": "https://api.x.ai/v1",
        }.get(provider) or os.environ.get("COUNCIL_BASE_URL") or sys.exit("Set COUNCIL_BASE_URL")
        key = {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "xai": os.environ.get("XAI_API_KEY"),
        }.get(provider, os.environ.get("COUNCIL_API_KEY", ""))
        if provider != "openai-compatible" and not key:
            sys.exit(f"Set the API key env var for {provider}")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        out = _post_json(
            base.rstrip("/") + "/chat/completions",
            headers,
            {"model": model, "messages": msgs},
        )
        return out["choices"][0]["message"]["content"]
    sys.exit(f"Unknown COUNCIL_PROVIDER: {provider}")


def _analyze_block(text: str, post_type: str | None, *, require_header: bool) -> dict:
    spec = spec_for(post_type)
    errors: list[str] = []
    scores: dict[str, int] = {}
    skipped: list[str] = []
    reasons: dict[str, str] = {}
    order: list[str] = []
    council_line: int | None = None
    post_type_line: str | None = None
    top_fixes: list[str] = []
    rewrite: str | None = None
    lines = text.splitlines()
    first = next((line for line in lines if line.strip()), "")
    if require_header and not first.startswith("SIMULATED COUNCIL:"):
        errors.append("missing simulation label")
    rewrite_at: int | None = None
    top_fix_at: int | None = None
    for index, line in enumerate(lines):
        if line.startswith("POST TYPE:"):
            post_type_line = line.split(":", 1)[1].strip()
        elif line.startswith("COUNCIL:"):
            match = re.search(r"(\d+)\s*/\s*100", line)
            if not match:
                errors.append("COUNCIL line has no n/100")
            else:
                council_line = int(match.group(1))
        elif line.startswith("TOP FIX:"):
            top_fixes.append(line.split(":", 1)[1].strip())
            top_fix_at = index
        elif line.startswith("REWRITE:"):
            rewrite_at = index + 1
            break
        else:
            match = _REVIEWER_LINE.match(line)
            if match:
                name = match.group(1).lower()
                token = match.group(2)
                rest = match.group(3).strip()
                order.append(name)
                reasons[name] = rest
                if token == "skipped":
                    skipped.append(name)
                elif re.fullmatch(r"\d+/10", token):
                    value = int(token.split("/", 1)[0])
                    if not 0 <= value <= 10:
                        errors.append(f"{name} score {value} is outside 0-10")
                    scores[name] = value
                else:
                    errors.append(f"bad score token for {name}: {token}")
    if rewrite_at is None:
        errors.append("missing REWRITE")
        rewrite = ""
    else:
        rewrite = "\n".join(lines[rewrite_at:]).strip()
        if rewrite == "":
            errors.append("empty REWRITE")
    if top_fix_at is not None and rewrite_at is not None:
        extra = [line for line in lines[top_fix_at + 1 : rewrite_at - 1] if line.strip()]
        if extra:
            errors.append("extra text between TOP FIX and REWRITE")
    if len(top_fixes) != 1:
        errors.append(f"expected exactly one TOP FIX, found {len(top_fixes)}")
    elif top_fixes[0] == "":
        errors.append("empty TOP FIX")
    if require_header and post_type is not None:
        if post_type_line is None:
            errors.append("missing POST TYPE line")
        else:
            got = post_type_line.lower()
            if spec["label"].lower() not in got and post_type not in got:
                errors.append(f"POST TYPE is {post_type_line!r}, expected {spec['label']}")
    expected_order = list(REVIEWERS)
    if order != expected_order:
        errors.append(
            "reviewer lines must be Ogilvy, Halbert, Schwartz, Sugarman, Hopkins, Cialdini"
        )
    for name in REVIEWERS:
        weight = spec["weights"][name]
        if weight == 0:
            if name in scores:
                errors.append(f"{name} is not seated for {spec['label']}")
            elif name not in skipped:
                errors.append(f"{name} must be marked skipped for {spec['label']}")
        else:
            if name not in scores:
                errors.append(f"{name} is seated and needs a score")
            if name in skipped:
                errors.append(f"{name} is seated and cannot be skipped")
        if name == spec["dissenter"] and name in reasons:
            if "[dissenter]" not in reasons[name].lower():
                errors.append(f"{name} is the designated dissenter and needs [dissenter]")
        if name == "schwartz" and name in scores and "awareness:" not in reasons.get(name, "").lower():
            errors.append("Schwartz's reason needs an awareness level")
    expected_score = None
    if all(name in scores for name in seated(post_type)):
        expected_score = council_score(scores, post_type)
        if council_line is not None and council_line != expected_score:
            errors.append(f"COUNCIL score {council_line} != weighted score {expected_score}")
    return {
        "errors": errors,
        "scores": scores,
        "skipped": skipped,
        "reasons": reasons,
        "council_score": council_line,
        "expected_score": expected_score,
        "top_fix": top_fixes[0] if len(top_fixes) == 1 else None,
        "rewrite": rewrite or "",
        "post_type_line": post_type_line,
    }


def analyze_output(text: str, post_type: str | None) -> dict:
    """Parse a council reply and list format errors. Does not call a model."""
    if post_type != "reel-hook":
        block = _analyze_block(text, post_type, require_header=True)
        block["parse_ok"] = not block["errors"]
        block["hooks"] = None
        block["best_hook"] = None
        return block

    errors: list[str] = []
    header: list[str] = []
    hooks: list[dict] = []
    best: int | None = None
    current: dict | None = None
    for line in text.splitlines():
        hook_match = _HOOK_HEAD.match(line.strip())
        best_match = _BEST_HOOK.match(line.strip())
        if hook_match:
            current = {"index": int(hook_match.group(1)), "lines": []}
            hooks.append(current)
            continue
        if best_match:
            best = int(best_match.group(1))
            continue
        if current is None:
            header.append(line)
        else:
            current["lines"].append(line)
    header_text = "\n".join(header).strip()
    first = next((line for line in header if line.strip()), "")
    if not first.startswith("SIMULATED COUNCIL:"):
        errors.append("missing simulation label")
    if not any(line.startswith("POST TYPE:") and "reel" in line.lower() for line in header):
        errors.append("missing POST TYPE reel hook line")
    if not hooks:
        errors.append("missing HOOK blocks")
    parsed_hooks = []
    for hook in hooks:
        block = _analyze_block("\n".join(hook["lines"]), "reel-hook", require_header=False)
        block["index"] = hook["index"]
        parsed_hooks.append(block)
        for err in block["errors"]:
            errors.append(f"hook {hook['index']}: {err}")
    indexes = [hook["index"] for hook in parsed_hooks]
    if indexes != list(range(1, len(indexes) + 1)):
        errors.append(f"hook indexes must be 1..n in order, found {indexes}")
    if best is None:
        errors.append("missing BEST HOOK")
    elif parsed_hooks and all(hook["expected_score"] is not None for hook in parsed_hooks):
        ranking = sorted(
            parsed_hooks,
            key=lambda hook: (-(hook["expected_score"] or 0), hook["index"]),
        )
        winner = ranking[0]["index"]
        if best != winner:
            errors.append(f"BEST HOOK is {best}, expected {winner}")
    return {
        "errors": errors,
        "parse_ok": not errors,
        "hooks": parsed_hooks,
        "best_hook": best,
        "scores": None,
        "rewrite": None,
        "top_fix": None,
        "council_score": None,
        "expected_score": None,
        "reasons": None,
        "skipped": None,
    }


def gate_analysis(original: str, analysis: dict, post_type: str | None) -> dict:
    """Run the slop gate on every rewrite in a parsed reply."""
    if post_type == "reel-hook":
        sources = split_hooks(original)
        flags: list[dict] = []
        per_hook = []
        hooks = analysis.get("hooks") or []
        if not hooks:
            flags.append(
                {
                    "kind": "parse",
                    "match": "rewrite",
                    "detail": "could not find a rewrite to check",
                }
            )
        for hook in hooks:
            index = hook["index"]
            source = sources[index - 1] if 1 <= index <= len(sources) else original
            result = slop_gate.check(source, hook.get("rewrite") or "")
            problems = char_limit_problems(hook.get("rewrite") or "", post_type)
            for problem in problems:
                result["flags"].append(
                    {"kind": "length", "match": problem, "detail": problem}
                )
                result["ok"] = False
            hook["slop_gate"] = result
            per_hook.append({"index": index, **result})
            flags.extend(result["flags"])
        return {"ok": not flags, "flags": flags, "hooks": per_hook}
    rewrite = analysis.get("rewrite")
    if rewrite is None:
        return {
            "ok": False,
            "flags": [
                {
                    "kind": "parse",
                    "match": "rewrite",
                    "detail": "could not find a rewrite to check",
                }
            ],
        }
    result = slop_gate.check(original, rewrite)
    for problem in char_limit_problems(rewrite, post_type):
        result["flags"].append({"kind": "length", "match": problem, "detail": problem})
        result["ok"] = False
    return result


def format_gate(result: dict) -> str:
    if result.get("ok"):
        return "SLOP GATE: pass"
    lines = ["SLOP GATE: fail"]
    for flag in result.get("flags", []):
        lines.append(f"- {flag['kind']}: {flag['match']} ({flag['detail']})")
    return "\n".join(lines)


def append_log(record: dict, log_path: Path | None) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_report(path: str) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    lines = [f"# {data['title']}", "", data.get("intro", ""), ""]
    lines += ["## Summary", "", "| # | Post (snippet) | Council | Top fix |", "|---|---|---|---|"]
    for index, post in enumerate(data["posts"], 1):
        snippet = post["text"].replace("\n", " ")
        snippet = snippet if len(snippet) <= 60 else snippet[:57] + "..."
        score = council_score(post["scores"], post.get("post_type"))
        lines.append(f"| {index} | {snippet} | {score} | {post['top_fix']} |")
    totals = {
        name: sum(post["scores"][name] for post in data["posts"]) / len(data["posts"])
        for name in REVIEWERS
    }
    average = sum(council_score(post["scores"], post.get("post_type")) for post in data["posts"]) / len(
        data["posts"]
    )
    lines += [
        "",
        f"Average council score: **{average:.1f}/100**",
        "",
        "Average per reviewer: " + ", ".join(f"{name.title()} {value:.1f}" for name, value in totals.items()),
        "",
    ]
    for index, post in enumerate(data["posts"], 1):
        score = council_score(post["scores"], post.get("post_type"))
        lines += [
            f"## {index}. {post['date']} - {post['url']}",
            "",
            "Original (exact text):",
            "",
            "```",
            post["text"],
            "```",
            "",
        ]
        if post.get("note"):
            lines += [f"Note: {post['note']}", ""]
        lines += ["| Reviewer | Score | Why |", "|---|---|---|"]
        for name in REVIEWERS:
            lines.append(f"| {name.title()} | {post['scores'][name]}/10 | {post['reasons'][name]} |")
        lines += [
            "",
            f"**Council: {score}/100**",
            "",
            f"**Top fix:** {post['top_fix']}",
            "",
            "**Rewrite:**",
            "",
            "```",
            post["rewrite"],
            "```",
            "",
        ]
        gate = slop_gate.check(post["text"], post.get("rewrite") or "")
        if gate["ok"]:
            lines += ["Slop gate: pass", ""]
        else:
            lines.append("Slop gate: fail")
            for flag in gate["flags"]:
                lines.append(f"- {flag['kind']}: {flag['match']} ({flag['detail']})")
            lines.append("")
    if data.get("footer"):
        lines += ["---", "", data["footer"], ""]
    return "\n".join(lines)


def report_payload(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    posts = []
    for post in data["posts"]:
        gate = slop_gate.check(post["text"], post.get("rewrite") or "")
        posts.append(
            {
                "id": post.get("id"),
                "council_score": council_score(post["scores"], post.get("post_type")),
                "slop_gate": gate,
            }
        )
    average = sum(item["council_score"] for item in posts) / len(posts)
    return {
        "version": VERSION,
        "cmd": "report",
        "title": data.get("title"),
        "average_council_score": average,
        "posts": posts,
    }


def _log_path(args: argparse.Namespace) -> Path | None:
    if getattr(args, "no_log", False):
        return None
    raw = getattr(args, "log", None) or str(DEFAULT_LOG)
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _emit(payload: dict, as_json: bool, text: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(text)


def _add_io_flags(parser: argparse.ArgumentParser, *, with_post: bool) -> None:
    if with_post:
        parser.add_argument("text", nargs="?", help="post text (or use --file)")
        parser.add_argument("--file")
        parser.add_argument("--voice", default=DEFAULT_VOICE)
        parser.add_argument("--context")
        parser.add_argument(
            "--type",
            default="",
            help="one-liner, quote-post, thread, ad, reel-hook (default: all six, equal weights)",
        )
    parser.add_argument("--json", action="store_true", help="print a JSON object")
    parser.add_argument("--log", default=str(DEFAULT_LOG), help="JSONL run log path")
    parser.add_argument("--no-log", action="store_true", help="do not append to the run log")


def main() -> None:
    ap = argparse.ArgumentParser(description="copy-council CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prompt", "run"):
        _add_io_flags(sub.add_parser(name), with_post=True)
    report = sub.add_parser("report")
    report.add_argument("json_path")
    report.add_argument("--out")
    _add_io_flags(report, with_post=False)
    args = ap.parse_args()

    if args.cmd == "report":
        markdown = render_report(args.json_path)
        payload = report_payload(args.json_path)
        payload["ts"] = _now()
        append_log(payload, _log_path(args))
        if args.out:
            Path(args.out).write_text(markdown, encoding="utf-8")
        _emit(payload, args.json, markdown)
        return

    try:
        post_type = normalize_type(args.type)
    except ValueError as exc:
        sys.exit(str(exc))
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    if not text:
        sys.exit("Give post text or --file")
    if post_type == "reel-hook":
        problem = hook_count_error(text)
        if problem:
            print(problem, file=sys.stderr)
            sys.exit(2)

    try:
        prompt = build_prompt(text, args.voice or None, args.context, post_type)
    except FileNotFoundError as exc:
        sys.exit(str(exc))

    spec = spec_for(post_type)
    base = {
        "version": VERSION,
        "cmd": args.cmd,
        "ts": _now(),
        "post_type": post_type or "unspecified",
        "label": spec["label"],
        "weights": spec["weights"],
        "dissenter": spec["dissenter"],
        "seated": seated(post_type),
        "char_cap": spec["char_cap"],
        "voice": args.voice,
    }
    if post_type == "reel-hook":
        base["hooks_in"] = split_hooks(text)
    else:
        base["post"] = text

    if args.cmd == "prompt":
        payload = {**base, "model_called": False, "prompt": prompt}
        append_log(payload, _log_path(args))
        _emit(payload, args.json, prompt)
        return

    ok, reason = model_status()
    if not ok:
        payload = {**base, "model_called": False, "skipped": reason, "prompt": prompt}
        append_log(payload, _log_path(args))
        if args.json:
            _emit(payload, True, "")
        else:
            print(prompt)
            print(f"\n[run skipped: {reason}]", file=sys.stderr)
        return

    raw = call_llm(prompt)
    analysis = analyze_output(raw, post_type)
    if post_type == "reel-hook":
        expected_hooks = len(split_hooks(text))
        parsed_hooks = len(analysis.get("hooks") or [])
        if parsed_hooks != expected_hooks:
            analysis["errors"].append(
                f"expected {expected_hooks} hook blocks, parsed {parsed_hooks}"
            )
            analysis["parse_ok"] = False
    gate = gate_analysis(text, analysis, post_type)
    payload = {
        **base,
        "model_called": True,
        "raw": raw,
        "parse_ok": analysis["parse_ok"],
        "errors": analysis["errors"],
        "council_score": analysis.get("council_score"),
        "scores": analysis.get("scores"),
        "reasons": analysis.get("reasons"),
        "top_fix": analysis.get("top_fix"),
        "rewrite": analysis.get("rewrite"),
        "hooks": _public_hooks(analysis.get("hooks")),
        "best_hook": analysis.get("best_hook"),
        "slop_gate": gate,
    }
    append_log(payload, _log_path(args))
    if args.json:
        _emit(payload, True, "")
    else:
        print(raw)
        print()
        print(format_gate(gate))
    if not gate.get("ok") or not analysis["parse_ok"]:
        sys.exit(1)


def _public_hooks(hooks: list[dict] | None) -> list[dict] | None:
    if hooks is None:
        return None
    public = []
    for hook in hooks:
        public.append(
            {
                "index": hook.get("index"),
                "council_score": hook.get("council_score"),
                "expected_score": hook.get("expected_score"),
                "scores": hook.get("scores"),
                "reasons": hook.get("reasons"),
                "top_fix": hook.get("top_fix"),
                "rewrite": hook.get("rewrite"),
                "slop_gate": hook.get("slop_gate"),
                "errors": hook.get("errors"),
            }
        )
    return public


if __name__ == "__main__":
    main()
