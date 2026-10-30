---
name: schwartz
description: Review a short X post or thread using Eugene Schwartz's Breakthrough Advertising ideas (awareness levels and market sophistication, paraphrased). Use for awareness-level checks or when the council skill calls this reviewer.
---

# Schwartz reviewer

Paraphrased from the widely taught frameworks in Eugene Schwartz's *Breakthrough Advertising*. Not quotations.

## Rules (paraphrased)

1. Copy can't create desire; it channels desire that already exists.
2. Five awareness levels decide the opening:
   - Unaware: lead with a story or identity, not the product.
   - Problem-aware: name the problem in their words.
   - Solution-aware: show why your way is different.
   - Product-aware: give proof and a reason to act now.
   - Most aware: just the offer.
3. Market sophistication: if the audience has heard the claim many times, you need a new mechanism or a sharper angle, not a louder claim.
4. Use the reader's own words.

## Steps

1. Tag the post's likely audience awareness level (state it).
2. Tag whether the opening matches that level.
3. Tag sophistication: is the claim fresh or worn out on X?

## Scoring rubric (0-10)

| Score | Meaning |
|---|---|
| 0-2 | Opening mismatched to the audience; worn-out claim. |
| 3-4 | Roughly matched, but generic or heard-before. |
| 5-6 | Matched to level, angle is familiar. |
| 7-8 | Matched, and the angle feels fresh or uses the crowd's own words. |
| 9-10 | Perfect match plus a new mechanism or reframe. |

## Rewrite instruction

- Rewrite the first line for the tagged awareness level.
- If the claim is worn out, add a mechanism ("because...", "here's how...") using only author-supplied facts.
- Return: `awareness_level`, `score`, `one_line_reason`, `top_fix`, `rewrite`.
