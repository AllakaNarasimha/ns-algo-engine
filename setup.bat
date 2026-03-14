@echo off
REM setup_and_test.bat — Setup virtualenv, install deps, run tests, and optional git cleanup
REM Run this from the repository root (double-click or run in cmd/powershell):
REM    setup_and_test.bat

SETLOCAL ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo ========== Creating virtual environment .venv ==========
python -m venv .venv

echo ========== Upgrading pip inside .venv ==========
.venv\Scripts\python.exe -m pip install --upgrade pip

if exist requirements.txt (
  echo ========== Installing runtime requirements.txt ==========
  .venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
  echo Skipping requirements.txt (not found)
)

if exist requirements-dev.txt (
  echo ========== Installing development requirements-dev.txt ==========
  .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
) else (
  echo Skipping requirements-dev.txt (not found)
)

echo ========== Running tests (pytest) ==========
.venv\Scripts\python.exe -m pytest -q || echo pytest returned non-zero exit code

echo ========== Installing pre-commit hooks (optional) ==========
.venv\Scripts\python.exe -m pip install pre-commit || echo pre-commit already installed or failed
if exist .venv\Scripts\pre-commit.exe (
  .venv\Scripts\pre-commit.exe install || echo pre-commit install failed
) else (
  echo pre-commit executable not found, skipping hook install
)

REM Optional: remove tracked __pycache__ entries if this is a git repo
where git >nul 2>&1
if %ERRORLEVEL%==0 (
  echo ========== Git cleanup: remove tracked __pycache__ files ==========
  git add .gitignore 2>nul || echo no .gitignore to add
  git commit -m "Update .gitignore" --no-verify 2>nul || echo no commit for .gitignore
  for /f "delims=" %%d in ('dir /s /b /ad __pycache__ 2^>nul') do (
    echo Removing from git index: %%d
    git rm -r --cached --ignore-unmatch "%%d" 2>nul || echo nothing to remove
  )
  git add . 2>nul
  git commit -m "Remove tracked __pycache__ directories" 2>nul || echo no changes to commit
) else (
  echo Git not found on PATH; skipping git cleanup
)

echo ========== Setup script finished ==========
ENDLOCAL
