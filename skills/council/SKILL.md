---
name: council
description: Run the full copy council on a short X post or thread - Ogilvy, Halbert, Schwartz, Sugarman, Hopkins and Cialdini each score it 0-10, then aggregate the scores, pick the single most useful fix, and write one final rewrite in the author's voice. Use when the user says "council this", "review my tweet", "score this post", or pastes a draft post.
---

# Copy council (orchestrator)

## Inputs

- `post`: the post text (or a thread, posts separated by a line with `---`).
- `voice`: a voice profile file (e.g. `voice/ankit.md`). If none is given, infer voice from the post itself and keep it.
- Optional `context`: what a quoted post says, the audience, the goal.

## Process

1. **Read the voice file.** Every rewrite must sound like the author, not like AI.
2. **Run each reviewer** in `skills/<name>/SKILL.md`, in this order: `ogilvy`, `halbert`, `schwartz`, `sugarman`, `hopkins`, `cialdini`. Each returns a 0-10 score, a one-line reason, and a top fix. Reviewers do not see each other's output.
3. **Aggregate.** `council_score = round(mean(scores) * 10)` on a 0-100 scale. Report the highest and lowest reviewer.
4. **Pick ONE top fix.** Choose the fix that would raise the most reviewer scores at once. Usually it's the first line or missing context. One fix, not a list.
5. **Final rewrite.** One version, in the author's voice, applying the top fix plus anything compatible. Rules:
   - Never invent facts, numbers, names, or stories. Use `[fact needed]` placeholders instead.
   - Stay under 280 characters per post.
   - Keep the author's language mix (e.g. light Hinglish) and punctuation habits.
   - If the original is already strong (council_score >= 75), the rewrite may be a light edit.

## Output format

```
COUNCIL: <council_score>/100
  Ogilvy    x/10  <reason>
  Halbert   x/10  <reason>
  Schwartz  x/10  <reason>  (awareness: <level>)
  Sugarman  x/10  <reason>
  Hopkins   x/10  <reason>
  Cialdini  x/10  <reason>
TOP FIX: <one sentence>
REWRITE:
<text>
```

Never post anything. The council writes; the author decides and publishes.
