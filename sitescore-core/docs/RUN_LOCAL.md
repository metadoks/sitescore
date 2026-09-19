# Run locally

## Linux / macOS

```bash
cd sitescore-core
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python examples/demo.py
```

## Windows PowerShell

```powershell
cd sitescore-core
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
pytest
python examples\demo.py
```

If editable installation is temporarily unavailable, tests can still run with:

```bash
PYTHONPATH=src pytest
```
