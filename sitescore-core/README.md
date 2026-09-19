# SiteScore Core v0.1-dev

Deterministic, API-independent calculation core for SiteScore AI.

## Principles

- Location Engine and Financial Engine are strictly decoupled.
- Model parameters live in immutable configuration objects.
- Same input + same model version => same output.
- Mathematical validation is not empirical business validation.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e '.[dev]'
pytest
```
