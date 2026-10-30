#!/usr/bin/env python3
"""copy-council CLI.

Build the council prompt for a post, optionally send it to an LLM, or render
a results JSON file into a markdown report. Standard library only.

Usage:
  python3 scripts/council.py prompt "your post text" [--voice voice/ankit.md] [--context "..."]
  python3 scripts/council.py prompt --file post.txt
  python3 scripts/council.py run "your post text"          # needs a provider (see README)
  python3 scripts/council.py report examples/ankit-10-tweets.json

Env vars for `run`:
  COUNCIL_PROVIDER   openai | anthropic | xai | openai-compatible   (default: none -> prints prompt)
  COUNCIL_MODEL      model name for that provider (required for run)
  OPENAI_API_KEY / ANTHROPIC_API_KEY / XAI_API_KEY   key for the chosen provider
  COUNCIL_BASE_URL   base URL for openai-compatible servers (e.g. http://localhost:11434/v1 for Ollama)
  COUNCIL_API_KEY    key for openai-compatible servers (optional)
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEWERS = ["ogilvy", "halbert", "schwartz", "sugarman", "hopkins", "cialdini"]


def read_skill(name: str) -> str:
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    # strip YAML frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text.strip()


def build_prompt(post: str, voice_path: str | None, context: str | None) -> str:
    parts = [
        "You are the copy council. Follow the orchestrator instructions exactly.",
        "## Orchestrator\n" + read_skill("council"),
    ]
    for r in REVIEWERS:
        parts.append(f"## Reviewer: {r}\n" + read_skill(r))
    parts.append("## Finance-safe check\n" + read_skill("finance-safe"))
    if voice_path:
        vp = Path(voice_path)
        if not vp.is_absolute():
            vp = ROOT / vp
        parts.append("## Author voice profile\n" + vp.read_text(encoding="utf-8").strip())
    if context:
        parts.append("## Context\n" + context.strip())
    parts.append("## Post to review\n```\n" + post.strip() + "\n```")
    parts.append("Return the output in the orchestrator's output format. Do not invent facts.")
    return "\n\n".join(parts)


def _post_json(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def call_llm(prompt: str) -> str:
    provider = os.environ.get("COUNCIL_PROVIDER", "none").lower()
    model = os.environ.get("COUNCIL_MODEL")
    if provider == "none":
        return prompt
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
        return "".join(b.get("text", "") for b in out.get("content", []))
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
        out = _post_json(base.rstrip("/") + "/chat/completions", headers, {"model": model, "messages": msgs})
        return out["choices"][0]["message"]["content"]
    sys.exit(f"Unknown COUNCIL_PROVIDER: {provider}")


def council_score(scores: dict) -> int:
    vals = [scores[r] for r in REVIEWERS]
    return round(sum(vals) / len(vals) * 10)


def render_report(path: str) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    lines = [f"# {data['title']}", "", data.get("intro", ""), ""]
    lines += ["## Summary", "", "| # | Post (snippet) | Council | Top fix |", "|---|---|---|---|"]
    for i, t in enumerate(data["posts"], 1):
        snip = t["text"].replace("\n", " ")
        snip = snip if len(snip) <= 60 else snip[:57] + "..."
        lines.append(f"| {i} | {snip} | {council_score(t['scores'])} | {t['top_fix']} |")
    totals = {r: sum(t["scores"][r] for t in data["posts"]) / len(data["posts"]) for r in REVIEWERS}
    avg = sum(council_score(t["scores"]) for t in data["posts"]) / len(data["posts"])
    lines += ["", f"Average council score: **{avg:.1f}/100**", "",
              "Average per reviewer: " + ", ".join(f"{r.title()} {v:.1f}" for r, v in totals.items()), ""]
    for i, t in enumerate(data["posts"], 1):
        lines += [f"## {i}. {t['date']} - {t['url']}", "", "Original (exact text):", "", "```", t["text"], "```", ""]
        if t.get("note"):
            lines += [f"Note: {t['note']}", ""]
        lines += ["| Reviewer | Score | Why |", "|---|---|---|"]
        for r in REVIEWERS:
            lines.append(f"| {r.title()} | {t['scores'][r]}/10 | {t['reasons'][r]} |")
        lines += ["", f"**Council: {council_score(t['scores'])}/100**", "", f"**Top fix:** {t['top_fix']}", "",
                  "**Rewrite:**", "", "```", t["rewrite"], "```", ""]
        flags = t.get("finance_flags", [])
        if flags:
            lines.append(f"**Finance-safe:** {t.get('finance_verdict', 'REVIEW')}")
            for f in flags:
                lines.append(f"- {f['severity']}: \"{f['phrase']}\" - {f['issue']} Fix: {f['fix']}")
        else:
            lines.append("**Finance-safe:** CLEAR - no flags.")
        lines.append("")
    if data.get("footer"):
        lines += ["---", "", data["footer"], ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="copy-council CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prompt", "run"):
        p = sub.add_parser(name)
        p.add_argument("text", nargs="?", help="post text (or use --file)")
        p.add_argument("--file")
        p.add_argument("--voice", default="voice/ankit.md")
        p.add_argument("--context")
    r = sub.add_parser("report")
    r.add_argument("json_path")
    r.add_argument("--out")
    a = ap.parse_args()

    if a.cmd == "report":
        md = render_report(a.json_path)
        if a.out:
            Path(a.out).write_text(md, encoding="utf-8")
        else:
            print(md)
        return
    text = Path(a.file).read_text(encoding="utf-8") if a.file else a.text
    if not text:
        sys.exit("Give post text or --file")
    prompt = build_prompt(text, a.voice or None, a.context)
    print(prompt if a.cmd == "prompt" else call_llm(prompt))


if __name__ == "__main__":
    main()
