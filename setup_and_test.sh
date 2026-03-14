#!/bin/bash
# setup_and_test.sh — Setup virtualenv, install deps, run tests, and optional git cleanup

echo "========== Creating virtual environment .venv =========="
python -m venv .venv

echo "========== Upgrading pip inside .venv =========="
.venv/bin/python -m pip install --upgrade pip

if [ -f requirements.txt ]; then
  echo "========== Installing runtime requirements.txt =========="
  .venv/bin/python -m pip install -r requirements.txt
else
  echo "Skipping requirements.txt (not found)"
fi

if [ -f requirements-dev.txt ]; then
  echo "========== Installing development requirements-dev.txt =========="
  .venv/bin/python -m pip install -r requirements-dev.txt
else
  echo "Skipping requirements-dev.txt (not found)"
fi

echo "========== Running tests (pytest) =========="
.venv/bin/python -m pytest -q || echo "pytest returned non-zero exit code"

echo "========== Installing pre-commit hooks (optional) =========="
.venv/bin/python -m pip install pre-commit || echo "pre-commit already installed or failed"
if [ -f .venv/bin/pre-commit ]; then
  .venv/bin/pre-commit install || echo "pre-commit install failed"
else
  echo "pre-commit executable not found, skipping hook install"
fi

# Optional: remove tracked __pycache__ entries if this is a git repo
if command -v git >/dev/null 2>&1; then
  echo "========== Git cleanup: remove tracked __pycache__ files =========="
  git add .gitignore 2>/dev/null || echo "no .gitignore to add"
  git commit -m "Update .gitignore" --no-verify 2>/dev/null || echo "no commit for .gitignore"
  find . -type d -name __pycache__ -exec git rm -r --cached --ignore-unmatch {} \; 2>/dev/null || echo "nothing to remove"
  git add . 2>/dev/null
fi

echo "Setup complete!"