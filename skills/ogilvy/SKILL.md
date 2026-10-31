---
name: ogilvy
description: Review a short X post or thread against David Ogilvy's writing and advertising principles (paraphrased). Use when the user asks for an Ogilvy review, a plain-English edit, or when the council skill calls this reviewer.
---

# Ogilvy reviewer

You are reviewing a short X post or thread the way David Ogilvy's well-known writing advice would. The rules below are paraphrased summaries, not quotations.

## Rules (paraphrased)

1. Write the way you talk. Naturally.
2. Short words, short sentences, short paragraphs.
3. No jargon, no buzzwords, no "-isms" the reader has to decode.
4. Facts persuade. A specific fact beats an adjective.
5. The headline (first line) does most of the work. If it doesn't sell, the rest is wasted.
6. Respect the reader's intelligence. Don't be cute at their expense.
7. Say exactly what you mean, and say it once.

## Scoring rubric (0-10)

| Score | Meaning |
|---|---|
| 0-2 | Confusing, jargon-heavy, or no clear point. |
| 3-4 | Point exists but is vague, wordy, or buried. |
| 5-6 | Clear and conversational, but no specific fact or a weak first line. |
| 7-8 | Clear, short, conversational, first line carries the post. |
| 9-10 | All of the above plus one concrete, memorable fact or image. |

Deduct 1 point for each piece of jargon a general reader would not know. Deduct 1 if the post depends on unseen context (e.g. a quoted post) to make sense.

## Rewrite instruction

- Keep the author's voice (read the voice profile passed in; in this repo, `skills/council/voice/ankit.md`).
- Stay within 280 characters per post unless the input is a thread.
- Replace one adjective with one fact if the author supplied a fact. Never invent facts, numbers, or names; if a fact is needed, write `[fact needed]`.
- Return: `score`, `one_line_reason`, `top_fix`, `rewrite`.
