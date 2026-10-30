---
name: finance-safe
description: Flag risky financial claims in marketing copy or social posts - promised or guaranteed returns, unverifiable claims, missing risk language - with SEBI-style caution for Indian fintech and investment copy. Use on any post that mentions returns, investing, markets, money, or a financial product, or when the council skill runs. Not legal or compliance advice.
---

# Finance-safe check

> **Not legal, regulatory, or compliance advice.** This is a hygiene check inspired by the general direction of Indian securities-market advertising norms (SEBI and exchange codes) and common fintech practice. Rules change. Anything going out on behalf of a regulated entity must be cleared by that entity's compliance team.

This skill does not score. It returns flags with a severity.

## What to flag

### HIGH
- **Promised or guaranteed returns**: "guaranteed", "assured returns", "fixed X% for sure", "risk-free", "can't lose", "100% safe", "sure-shot".
- **Return projections stated as fact**: "you will earn 12%", "double your money".
- **Past performance as promise**: "gave 14% last year, so you'll get it too".
- **Comparisons to FDs or other products implying equal safety** without noting the different risk.
- **Unverifiable "no defaults ever / zero loss" claims** without a date, source, or scope ("as of [date], per [source]").

### MEDIUM
- **Unverifiable claims**: "best", "No. 1", "most trusted", "everyone is making money" with no source.
- **Missing risk language** on a post that names a product, return, or investment action. Suggest a short line such as "Investments are subject to market and credit risk. Read all documents carefully."
- **Urgency/pressure on an investment**: "last chance", "only today" tied to investing.
- **Missing disclosure** when the author works at or is paid by the platform they're praising ("I work at X").

### LOW
- **Generalised money opinions** ("optimists make money") - fine as personal opinion; avoid reusing in brand ads.
- **Quotes about markets** with doubtful attribution or wording.

## Output

```
finance_flags:
  - severity: HIGH|MEDIUM|LOW
    phrase: "<exact phrase>"
    issue: "<why>"
    fix: "<safer wording>"
verdict: CLEAR | REVIEW | BLOCK   # BLOCK if any HIGH, REVIEW if any MEDIUM
disclaimer: "Not legal advice."
```

If the post has nothing financial in it, return `finance_flags: []` and `verdict: CLEAR`.
