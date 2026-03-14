# ns-algo-engine

Minimal setup and developer instructions.

Setup (venv + pip):

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Install development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run tests:

```powershell
pytest -q
```

Pre-commit hooks (optional):

```powershell
pre-commit install
pre-commit run --all-files
```
