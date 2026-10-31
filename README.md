# copy-council

Get your copy tested by the best marketers of our generation and before.

Six classic copywriters review your X post. You get one score, one fix, and one rewrite in your own voice.

Repository: https://github.com/GallivantGujju/copy-council

Version 1.0.0. See [CHANGELOG.md](CHANGELOG.md).

`copy-council` is a set of agent skills (Claude Code, Cursor, any tool that reads `SKILL.md` folders) and plain prompts. It runs a short post or thread past six reviewers, each built on paraphrased principles from a classic of advertising and persuasion:

| Reviewer | Built on | Asks |
|---|---|---|
| `ogilvy` | David Ogilvy's writing and advertising advice | Is it plain, short, and factual? Does the first line sell? |
| `halbert` | Gary Halbert, *The Boron Letters* | Who's the starving crowd? Does it feel like a note, not an ad? |
| `schwartz` | Eugene Schwartz, *Breakthrough Advertising* | Does the opening match the reader's awareness level? Is the angle worn out? |
| `sugarman` | Joseph Sugarman's "slippery slide" | Does every line get the next one read? Where would someone stop? |
| `hopkins` | Claude Hopkins, *Scientific Advertising* | Is anything specific, useful, testable? |
| `cialdini` | Robert Cialdini, *Influence* | Which persuasion levers are used, and honestly? |

Plus **`council`**: the orchestrator. It weights the reviewers for the post type, picks the one fix that helps most, and writes one final rewrite in the author's voice. The voice file ships inside the council skill at `skills/council/voice/ankit.md`.

## How this differs from marketing-council

[coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (MIT) includes a marketing-council skill. That skill seats a simulated board, including Ogilvy, Schwartz, Hopkins and Halbert, and talks through a strategy question.

copy-council scores a short post, gives one fix, and rewrites it in the author's voice. It also scores a list of Reel hooks. It borrows two ideas from marketing-council, with credit in [NOTICE.md](NOTICE.md): a designated dissenter (one reviewer argues the other way) and grounding rules (label the session as a simulation, no fabricated quotes, no invented facts).

## Repo layout

```
copy-council/
├── README.md
├── CHANGELOG.md
├── NOTICE.md
├── LICENSE
├── VERSION
├── skills/
│   ├── council/SKILL.md
│   ├── council/voice/ankit.md
│   ├── ogilvy/SKILL.md
│   ├── halbert/SKILL.md
│   ├── schwartz/SKILL.md
│   ├── sugarman/SKILL.md
│   ├── hopkins/SKILL.md
│   └── cialdini/SKILL.md
├── scripts/
│   ├── council.py
│   ├── slop_gate.py
│   ├── run_evals.py
│   ├── calibrate.py
│   └── check_links.py
├── evals/cases.json
├── calibration/example-posts.csv
└── examples/
```

## Install

Each skill is a folder whose name matches the `name` field in its `SKILL.md`. The council voice file is inside that folder, so one install brings it along. Tested with `npx skills add` against this repo: Claude Code received `skills/council/voice/ankit.md` under the council skill, and so did Cursor.

Pass the agent flag. Without it, the CLI can install the files where that agent does not look.

### Claude Code

```bash
npx skills add GallivantGujju/copy-council -a claude-code -y
```

Project install writes `.claude/skills/<name>/SKILL.md`. Add `-g` for `~/.claude/skills/<name>/SKILL.md`. The folder name matches `name` (`council`, `ogilvy`, and the other reviewers). The voice file lands at `.claude/skills/council/voice/ankit.md`.

### Cursor

Cursor loads a skill from `.cursor/skills/<name>/SKILL.md` or `.agents/skills/<name>/SKILL.md`. The folder name must match `name`. Docs: https://cursor.com/docs/skills

```bash
npx skills add GallivantGujju/copy-council -a cursor -y
```

In the skills CLI used for the local test, a project install wrote `.agents/skills/<name>/SKILL.md`, which Cursor loads. A global install (`-g`) wrote `~/.agents/skills/<name>/SKILL.md`, which Cursor also loads. The voice file was at `.agents/skills/council/voice/ankit.md`.

To put the skills on the `.cursor/skills/` path specifically:

```bash
mkdir -p .cursor/skills
cp -a skills/. .cursor/skills/
```

That gives `.cursor/skills/council/SKILL.md` and `.cursor/skills/council/voice/ankit.md`. The folder `council` matches `name: council`.

Restart the agent, then:

```
council this: "AI took away every excuse. If you're still not creating content, the problem was never time, skill or tools."
```

`npx skills add GallivantGujju/copy-council` installs whatever is on the default branch. This layout is what that command picks up once 1.0.0 is on that branch.

## Post types

The score is `round(sum(score × weight) / sum(weight) × 10)` over seated reviewers. `round` is Python's round (a half goes to the nearest even integer). Weight 0 means the reviewer is skipped. These are house weights, not a fit to engagement. The same table is in `skills/council/SKILL.md` and `scripts/council.py`.

| Type | Ogilvy | Halbert | Schwartz | Sugarman | Hopkins | Cialdini | Dissenter | Cap |
|---|---|---|---|---|---|---|---|---|
| one-liner | 1 | 1 | 1 | 1 | 0 | 0.5 | schwartz | 280 |
| quote-post | 1.5 | 1 | 1 | 1 | 0.5 | 1 | ogilvy | 280 |
| thread | 1 | 1 | 1 | 1.5 | 1 | 1 | hopkins | 280 |
| ad | 1.5 | 1 | 1 | 1 | 1.5 | 1 | halbert | none |
| reel-hook | 1 | 0 | 1 | 1 | 0 | 0 | schwartz | none |

`ad` is ad/landing copy. `reel-hook` seats Ogilvy, Sugarman and Schwartz only.

Hopkins is skipped on a one-liner. A one-line opinion cannot carry proof, so that score does not enter the average. Omit `--type` and the script seats all six at weight 1, which is how the example report below was scored.

The designated dissenter's reason includes `[dissenter]` and states the strongest case against the post. The reply starts with `SIMULATED COUNCIL: paraphrased principles, not a review by these people.`

Clarity, voice, specificity, persuasion and scannability are mapped onto the reviewers. That split is adapted from the copy-editing skill in marketingskills (MIT). See [NOTICE.md](NOTICE.md).

## The script

`scripts/council.py` uses only the Python 3.10+ standard library.

```bash
python3 scripts/council.py prompt "your post" --type one-liner --voice skills/council/voice/ankit.md
python3 scripts/council.py prompt --file draft.txt --type quote-post --context "Quote-post of a news story"
python3 scripts/council.py run "your post" --type one-liner --json
python3 scripts/council.py report examples/ankit-10-tweets.json --out examples/ankit-10-tweets.md
```

`--json` prints one JSON object. Every command appends a line to `runs/council.jsonl` unless you pass `--no-log`.

Reel-hook mode, for reels-india or anyone with 3 to 6 hooks (one per line, or separated by a line that is only `---`):

```bash
python3 scripts/council.py run --type reel-hook --file hooks.txt --json
```

Seated reviewers are Ogilvy, Sugarman and Schwartz only. Exit 2 if the file does not contain 3 to 6 hooks. The JSON `hooks` array has `index`, `scores`, `council_score`, `top_fix`, `rewrite` and `slop_gate`. `best_hook` is the highest score, and a tie goes to the earlier hook. The full shape is in `skills/council/SKILL.md`.

| Env var | Used for |
|---|---|
| `COUNCIL_PROVIDER` | `anthropic`, `openai`, `xai`, `openai-compatible`, or `none`. With `none` (the default), `run` prints the prompt and does not call a model. |
| `COUNCIL_MODEL` | Model name for the provider. |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY` | API key for that provider. |
| `COUNCIL_BASE_URL` | Base URL for an OpenAI-compatible server. |
| `COUNCIL_API_KEY` | Optional key for that server. |

On `run`, a rewrite that fails the slop gate or the output format exits 1. The reply is still printed.

## Slop gate

`scripts/slop_gate.py` is deterministic. It flags banned words and phrases (including "delve" and "It's not X, it's Y") and any digit number in the rewrite that is not in the original. The author's hyphen-dash, as in `limits- kaam`, is allowed. `scripts/council.py` runs the gate on every rewrite. The pattern list is a small subset inspired by blader/humanizer (MIT). See [NOTICE.md](NOTICE.md).

```bash
python3 scripts/slop_gate.py --original "your post" --rewrite "the rewrite"
```

Exit 0 when the rewrite is clean, 1 when it is flagged.

## Evals

`evals/cases.json` holds 30 cases. `scripts/run_evals.py` checks output format, a rewrite of at most 280 characters for X posts, exactly one fix, no number that the original does not already contain, post-type weights, and the reel-hook count. The consistency check scores one post three times and passes when each seated reviewer stays within ±1. It runs only when `COUNCIL_PROVIDER` and `COUNCIL_MODEL` (and the key that provider needs) are set. Otherwise it prints SKIP and exits 0.

```bash
python3 scripts/run_evals.py
python3 scripts/check_links.py
```

`.github/workflows/checks.yml` runs both on push and pull request.

## Calibration

`scripts/calibrate.py` reads a CSV of `post_text` plus public metrics (`impressions`, `likes`, `reposts`, `replies`, `bookmarks`, `quotes`) and writes Pearson r between the council score and each metric. A blank `council_score` is filled by a council run when a model is configured, and left blank with a skip note when it is not. Correlation is not defined when a column does not vary.

`calibration/example-posts.csv` is a two-row fixture. Every row is labelled `EXAMPLE_NOT_REAL`. The numbers in it are placeholders so the script can run. They are not measurements and not a published result.

```bash
python3 scripts/calibrate.py calibration/example-posts.csv
```

## Example output

From `examples/ankit-10-tweets.md`, scored with equal weights before post-type weighting:

```
POST: Why is everyone so proud of using codex or Claude's limits- kaam karo na.
      Show what you have used that exhausted limit for.

COUNCIL: 65/100
  Ogilvy    7/10  Conversational and direct; one long run-on sentence.
  Halbert   7/10  Speaks straight to AI-power-user Twitter with a challenge.
  Schwartz  7/10  Problem-aware crowd; calling out the 'limit flex' is fresh.
  Sugarman  6/10  The question opens well; the second sentence is wordy.
  Hopkins   6/10  Asks for proof, which is Hopkins' whole point.
  Cialdini  6/10  Social proof in reverse: show real work, not limits.
TOP FIX: Tighten into two short lines: the claim, then the ask.
REWRITE:
Hitting your Claude or Codex limit isn't a flex- kaam karo na.
Show what you built with it.
```

Across 10 real posts the council averaged 52/100. Hopkins was the harshest reviewer (3.7/10 on average) and Sugarman the kindest (5.9/10). The report now also runs the slop gate on those rewrites. The Pareto post's rewrite says "top 20%"; 20 is not in the original, so the gate flags it. The hyphen in the rewrite above is allowed.

## Make it yours

1. Copy `skills/council/voice/ankit.md` to a new file next to it.
2. Feed your last 25-100 posts to any model and ask it to fill in the same headings: shape, tone, language mix, punctuation, topics, never.
3. Pass `--voice` with that file, or tell the council skill which voice file to use.

## Credits and disclaimer

- The reviewer rules are paraphrased summaries of widely taught ideas from David Ogilvy, Gary Halbert, Eugene Schwartz, Joseph Sugarman, Claude Hopkins and Robert Cialdini. They are not quotations and not official material. Read the books.
- This project has no affiliation with, or endorsement from, these authors or their estates.
- Borrowed ideas and their MIT copyright lines are in [NOTICE.md](NOTICE.md).
- Scores are a model's (or a person's) judgment against a rubric. They don't predict engagement.
- The skills never publish anything. They write; you decide.

MIT licensed.
