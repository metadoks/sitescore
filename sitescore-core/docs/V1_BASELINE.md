# SiteScore AI V1 Baseline

This repository implements the locked V1 deterministic core.

## Core invariants

- Location and Financial engines are strictly decoupled.
- Category and sub-feature weights are immutable configuration.
- Dealbreaker penalties are smooth quadratic penalties.
- `T=0` disables penalty evaluation for that category.
- Penalties do not stack; the lowest multiplier dominates.
- Decision classification uses Location Score + Base BEC only.
- RBI, downside BEC and operating margin are diagnostics/risk flags.
- Confidence measures data/input quality, not probability of business success.
- Same input + same model version must produce the same output.
- Empirical business validity is still pending.
