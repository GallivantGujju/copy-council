# Changelog

## 1.0.0 - 2026-10-31

- Voice profiles live in `skills/council/voice/`, so installing the council skill brings the voice file with it.
- Post-type weights for a one-liner, a quote-post, a thread, ad/landing copy, and a Reel hook. Hopkins is not seated on a one-liner.
- Reel-hook mode seats Ogilvy, Sugarman and Schwartz and scores 3 to 6 hooks.
- `scripts/slop_gate.py` flags banned patterns and any number in a rewrite that is not in the original. `scripts/council.py` runs it on every rewrite. The author's hyphen-dash stays allowed.
- `--json` output and a JSONL run log at `runs/council.jsonl`.
- `evals/` with a deterministic runner. The consistency check runs only when a model is configured.
- `scripts/calibrate.py` scores a CSV of post text and public metrics. The only bundled file is a labelled example fixture, not a measurement.
- Designated dissenter and grounding rules adapted from Corey Haines's marketing-council skill (MIT). See NOTICE.md.
- The finance-safe skill is not part of this release.
