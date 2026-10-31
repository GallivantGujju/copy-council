---
name: council
description: Score a short X post, thread, ad, or a list of 3-6 Reel hooks. Reviewers are Ogilvy, Halbert, Schwartz, Sugarman, Hopkins and Cialdini, weighted by post type. The council then picks one fix and rewrites in the author's voice. Use when the user says "council this", "review my tweet", "score this post", "score these hooks", or pastes a draft.
metadata:
  version: 1.0.0
---

# Copy council (orchestrator)

Version 1.0.0. The folder name `council` matches `name`.

Six simulated reviewers score one post. You return one weighted score, one fix, and one rewrite in the author's voice. Reviewer rules are paraphrases, not quotations.

## Inputs

- `post`: the post text. A thread is posts separated by a line that is only `---`.
- `voice`: a voice profile. This skill ships `voice/ankit.md` (repo path `skills/council/voice/ankit.md`). If none is given, infer voice from the post and keep it.
- `context`: optional. What a quoted post says, who the reader is, what the post is for.
- `post type`: `one-liner`, `quote-post`, `thread`, `ad` (ad/landing copy), or `reel-hook`. If the user does not name one, pick the closest and say which you picked.

## Dimensions

The separate-dimension idea is adapted from Corey Haines's copy-editing skill (MIT). See NOTICE.md. This mapping is a house rule.

| Dimension | Reviewer |
|---|---|
| Clarity | Ogilvy |
| Voice (sounds like a person) | Halbert, plus the voice file |
| Specificity | Hopkins |
| Persuasion | Cialdini |
| Scannability (the next line gets read) | Sugarman |
| Awareness and angle | Schwartz |

## Post-type weights

House weights, not fitted to engagement. Weight 0 means that reviewer is skipped and does not enter the average.

`council_score = round(sum(score × weight) / sum(weight) × 10)` over seated reviewers. `round` is Python's round: a half goes to the nearest even integer.

| Type | Ogilvy | Halbert | Schwartz | Sugarman | Hopkins | Cialdini | Dissenter | Cap |
|---|---|---|---|---|---|---|---|---|
| one-liner | 1 | 1 | 1 | 1 | 0 | 0.5 | schwartz | 280 |
| quote-post | 1.5 | 1 | 1 | 1 | 0.5 | 1 | ogilvy | 280 |
| thread | 1 | 1 | 1 | 1.5 | 1 | 1 | hopkins | 280 |
| ad | 1.5 | 1 | 1 | 1 | 1.5 | 1 | halbert | none |
| reel-hook | 1 | 0 | 1 | 1 | 0 | 0 | schwartz | none |

`ad` means ad/landing copy. Cap is a raw character count per post, not X's shortened-URL count. A thread is capped on each post. `none` means there is no 280 cap.

Hopkins is 0 on a one-liner. A one-line opinion cannot carry proof, so Hopkins does not enter the average. He is seated on threads and ads, and at half weight on a quote-post, where the proof may sit in the quoted card.

Cialdini is half weight on a one-liner so a missing persuasion lever does not count as much as clarity. Sugarman is 1.5 on a thread because the slide across posts is the question. Ogilvy and Hopkins are 1.5 on ad/landing copy. Ogilvy is 1.5 on a quote-post because the line has to stand without the quoted card.

Untyped runs (no post type passed to `scripts/council.py`) seat all six at weight 1. That keeps the older equal-weight average.

## Designated dissenter

One seated reviewer argues the other way. Their reason states the strongest case against the post and includes the marker `[dissenter]`. The marker is not a veto. Their score still uses the weight above.

This rule is adapted from the designated dissenter in Corey Haines's marketing-council skill (MIT). See NOTICE.md.

| Type | What the dissenter pushes on |
|---|---|
| one-liner | Schwartz: the angle is worn out |
| quote-post | Ogilvy: the line does not stand alone |
| thread | Hopkins: where is the proof |
| ad | Halbert: it feels like an ad, not a note |
| reel-hook | Schwartz: the hook is worn out |

## Grounding

Adapted from the grounding rules in that marketing-council skill.

- Start with this exact line: `SIMULATED COUNCIL: paraphrased principles, not a review by these people.`
- Do not write quotations from these people.
- Do not invent facts, numbers, names, or stories. Use `[fact needed]` when a detail is missing.
- Do not imply that the real person reviewed this post.
- The dissenter disagrees with the post, not with a cartoon of another reviewer.

## Process

1. Read the voice file. The rewrite sounds like the author, including a hyphen used as a dash (`limits- kaam`).
2. Name the post type and seat the reviewers in the weight table. Skip weight 0. Reviewers do not see each other's scores.
3. Aggregate with the formula above.
4. Pick one top fix. The fix that would raise the most seated scores at once. One fix, not a list.
5. Write one rewrite that applies that fix. Stay inside the cap. Keep the author's language mix.
6. Check the rewrite with `scripts/slop_gate.py` before you return it. The script flags banned patterns (including "It's not X, it's Y" and words such as "delve") and any number that is not in the original. The author's hyphen-dash is allowed. `scripts/council.py run` runs this gate on every rewrite.
7. If the seated score is 75 or higher, the rewrite may be a light edit.

## Output format

```
SIMULATED COUNCIL: paraphrased principles, not a review by these people.
POST TYPE: <one-liner|quote-post|thread|ad/landing copy|reel hook>
COUNCIL: <score>/100
  Ogilvy    <0-10>/10  <reason>            [dissenter] if Ogilvy is the dissenter
  Halbert   <0-10>/10  <reason>            [dissenter] if Halbert is the dissenter
  Schwartz  <0-10>/10  <reason>  (awareness: <level>)  [dissenter] if Schwartz is the dissenter
  Sugarman  <0-10>/10  <reason>
  Hopkins   <0-10>/10  <reason>            or: skipped  <why>
  Cialdini  <0-10>/10  <reason>            or: skipped  <why>
TOP FIX: <one sentence>
REWRITE:
<text>
```

A skipped reviewer is a line, not an omission: `Hopkins   skipped  <why>`. Schwartz, when seated, states the awareness level. Exactly one `TOP FIX` line, then `REWRITE:` on the next line. No bullet list of fixes.

For a thread, separate rewrite posts with a line that is only `---`. Each of those posts is at most 280 characters.

## Reel-hook interface

Short mode for a list of hooks, so reels-india can call it. Seated reviewers are Ogilvy, Sugarman and Schwartz only. Halbert, Hopkins and Cialdini are `skipped`.

Input: 3 to 6 hooks. One hook per line, or hooks separated by a line that is only `---` when a hook needs more than one line.

```
Show the bill, then the fix.
Stop scrolling for this.
Your first salary, itemised.
```

From a checkout of this repo:

```bash
python3 scripts/council.py run --type reel-hook --file hooks.txt --json
```

`prompt` instead of `run` builds the prompt and does not call a model. `--json` prints one JSON object. The run log is `runs/council.jsonl` unless you pass `--no-log`.

Exit 2 when the file does not contain 3 to 6 hooks. Exit 1 when the reply is off-format or the slop gate flags a rewrite. Exit 0 when the reply parses and the gate is clean.

JSON fields reels-india can rely on:

- `post_type`: `reel-hook`
- `seated`: `ogilvy`, `sugarman`, `schwartz`
- `hooks[]`: `index`, `scores`, `council_score`, `top_fix`, `rewrite`, `slop_gate`
- `best_hook`: the highest council score. A tie goes to the earlier hook.

Text shape:

```
SIMULATED COUNCIL: paraphrased principles, not a review by these people.
POST TYPE: reel hook

HOOK 1:
COUNCIL: <score>/100
  Ogilvy    <n>/10  <reason>
  Halbert   skipped  Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.
  Schwartz  <n>/10  <reason>  (awareness: <level>) [dissenter]
  Sugarman  <n>/10  <reason>
  Hopkins   skipped  Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.
  Cialdini  skipped  Reel-hook mode seats Ogilvy, Sugarman and Schwartz only.
TOP FIX: <one sentence>
REWRITE:
<one hook>

HOOK 2:
...
BEST HOOK: 1
```

The council does not post anything. It writes; the author decides.
