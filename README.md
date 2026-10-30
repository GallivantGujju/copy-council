# copy-council

Get your copy tested by the best marketers of our generation and before.

Six classic copywriters review your X post. You get one score, one fix, and one rewrite in your own voice.

Repository: https://github.com/GallivantGujju/copy-council

`copy-council` is a set of agent skills (Claude Code, Cursor, any tool that reads `SKILL.md` folders) and plain prompts. It runs a short post or thread past six reviewers, each built on paraphrased principles from a classic of advertising and persuasion:

| Reviewer | Built on | Asks |
|---|---|---|
| `ogilvy` | David Ogilvy's writing and advertising advice | Is it plain, short, and factual? Does the first line sell? |
| `halbert` | Gary Halbert, *The Boron Letters* | Who's the starving crowd? Does it feel like a note, not an ad? |
| `schwartz` | Eugene Schwartz, *Breakthrough Advertising* | Does the opening match the reader's awareness level? Is the angle worn out? |
| `sugarman` | Joseph Sugarman's "slippery slide" | Does every line get the next one read? Where would someone stop? |
| `hopkins` | Claude Hopkins, *Scientific Advertising* | Is anything specific, useful, testable? |
| `cialdini` | Robert Cialdini, *Influence* | Which persuasion levers are used, and honestly? |

Plus:

- **`council`**: the orchestrator. It runs all six, averages them into a 0-100 score, picks the one fix that helps most, and writes one final rewrite in the author's voice.
- **`finance-safe`**: flags promised or guaranteed returns, claims nobody can check, and missing risk language. It is tuned for SEBI-style caution in Indian fintech copy. **Not legal advice.**
- **`voice/`**: voice profiles the rewrites follow. `voice/ankit.md` is the author's own.

## Repo layout

```
copy-council/
├── README.md
├── LICENSE
├── skills/
│   ├── council/SKILL.md        # orchestrator
│   ├── ogilvy/SKILL.md
│   ├── halbert/SKILL.md
│   ├── schwartz/SKILL.md
│   ├── sugarman/SKILL.md
│   ├── hopkins/SKILL.md
│   ├── cialdini/SKILL.md
│   └── finance-safe/SKILL.md
├── voice/ankit.md              # example voice profile
├── scripts/council.py          # prompt builder / optional LLM runner / report renderer
└── examples/
    ├── ankit-10-tweets.json    # raw council results
    ├── ankit-10-tweets.md      # rendered report
    └── launch-thread.md
```

## Install

### Claude Code

```bash
git clone https://github.com/GallivantGujju/copy-council.git copy-council
mkdir -p ~/.claude/skills
cp -r copy-council/skills/* ~/.claude/skills/
cp -r copy-council/voice ~/.claude/skills/council/voice
```

Restart Claude Code, then:

```
council this: "AI took away every excuse. If you're still not creating content, the problem was never time, skill or tools."
```

Want it for one project only? Copy the folders into that project's `.claude/skills/` instead.

### Cursor (and other Agent Skills tools)

Copy `skills/*` into your project's skills folder (for example `.cursor/skills/` or `.agents/skills/`, whichever your tool reads), and keep `voice/` next to them. Then ask the agent to "run the council skill on this post".

### Plain prompt (ChatGPT, Grok, Claude.ai, anything)

```bash
python3 scripts/council.py prompt "your post here" > prompt.txt
```

Paste `prompt.txt` into any chat model. It bundles the orchestrator, all six reviewers, the finance-safe check, and your voice file into one prompt.

## The script

`scripts/council.py` uses only the Python 3.10+ standard library. You don't need an API key to build the prompt or render a report.

```bash
# From the repository root
cd copy-council

# Build the full council prompt (no API key needed)
python3 scripts/council.py prompt "your post" --voice voice/ankit.md
python3 scripts/council.py prompt --file draft.txt --context "Quote-post of a news story about X"

# Render a results JSON into a markdown report (no API key needed)
python3 scripts/council.py report examples/ankit-10-tweets.json --out examples/ankit-10-tweets.md

# Optional: send the prompt to an LLM you choose
export COUNCIL_PROVIDER=anthropic      # or openai | xai | openai-compatible
export COUNCIL_MODEL=<model-name>
export ANTHROPIC_API_KEY=...           # or OPENAI_API_KEY / XAI_API_KEY
python3 scripts/council.py run "your post"
```

| Env var | Used for |
|---|---|
| `COUNCIL_PROVIDER` | `anthropic`, `openai`, `xai`, `openai-compatible`, or `none`. With `none` (the default), `run` just prints the prompt. |
| `COUNCIL_MODEL` | Model name for the provider (required for `run`). |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY` | API key for that provider. |
| `COUNCIL_BASE_URL` | Base URL for an OpenAI-compatible server, e.g. a local Ollama at `http://localhost:11434/v1`. |
| `COUNCIL_API_KEY` | Optional key for that server. |

Score math: `council_score = round(mean(six reviewer scores) * 10)`.

## Example output

From `examples/ankit-10-tweets.md`:

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
FINANCE-SAFE: CLEAR
```

Across 10 real posts the council averaged 52/100. Hopkins was the harshest reviewer (3.7/10 on average) and Sugarman the kindest (5.9/10).

## Make it yours

1. Copy `voice/ankit.md` to `voice/<you>.md`.
2. Feed your last 25-100 posts to any model and ask it to fill in the same headings: shape, tone, language mix, punctuation, topics, never.
3. Pass `--voice voice/<you>.md`, or tell the council skill which voice file to use.

## Credits and disclaimer

- The reviewer rules are **paraphrased summaries** of widely taught ideas from David Ogilvy, Gary Halbert, Eugene Schwartz, Joseph Sugarman, Claude Hopkins and Robert Cialdini. They are not quotations and not official material. Read the books; they're better than any skill.
- This project has no affiliation with, or endorsement from, these authors or their estates.
- Scores are a model's (or a person's) judgment against a rubric. They don't predict engagement.
- `finance-safe` is a hygiene check inspired by the general direction of Indian securities-market advertising norms. It is **not legal, regulatory or compliance advice**. Copy from regulated entities needs sign-off from their own compliance team.
- The skills never publish anything. They write; you decide.

MIT licensed.
