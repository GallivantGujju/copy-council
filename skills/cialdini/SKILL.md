---
name: cialdini
description: Review a short X post or thread for Robert Cialdini's persuasion principles (paraphrased) - and flag misuse. Use for persuasion checks, fake-scarcity or fake-proof detection, or when the council skill calls this reviewer.
---

# Cialdini reviewer

Paraphrased from the principles popularised in Robert Cialdini's *Influence* and *Pre-Suasion*. Not quotations.

## Principles

Reciprocity, commitment and consistency, social proof, authority, liking, scarcity, unity (shared identity).

## Steps

1. List which principles the post uses (if any), quoting the phrase that uses it.
2. Flag misuse: fake scarcity, invented social proof, borrowed authority without credit, pressure tactics.
3. Suggest one ethical principle that would fit the post naturally.

## Scoring rubric (0-10)

| Score | Meaning |
|---|---|
| 0-2 | No persuasive lever, or a manipulative one. |
| 3-4 | Weak or accidental lever. |
| 5-6 | One honest lever, lightly used. |
| 7-8 | One or two honest levers that fit the author and audience. |
| 9-10 | Levers feel natural and make the reader want to act or belong. |

Any misuse caps the score at 3.

## Rewrite instruction

- Add at most one lever, honestly (e.g. unity via a shared identity the author has; reciprocity via a useful tip).
- Never invent numbers of people, testimonials, or deadlines.
- Return: `principles_used`, `misuse_flags`, `score`, `one_line_reason`, `top_fix`, `rewrite`.
