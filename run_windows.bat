@echo off
setlocal

REM --- Choose Python (prefer py -3, fallback to python) ---
set "PY_CMD="
where py >nul 2>nul && (py -3 -c "import sys" >nul 2>nul && set "PY_CMD=py -3")
if not defined PY_CMD (
  where python >nul 2>nul && (python -c "import sys" >nul 2>nul && set "PY_CMD=python")
)
if not defined PY_CMD (
  echo [ERROR] Python not found. Please install Python 3 from https://www.python.org/downloads/
  pause
  exit /b 1
)

cd /d "%~dp0"

REM --- Create venv if missing ---
if not exist ".venv\\Scripts\\python.exe" (
  echo Creating virtual environment in .venv ...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :error
)

set "VENV_PY=.venv\\Scripts\\python.exe"

REM --- Upgrade pip and install dependencies (lite) ---
%VENV_PY% -m pip install --upgrade pip
if errorlevel 1 goto :error

%VENV_PY% -m pip install -r requirements-lite.txt
if errorlevel 1 goto :error

echo.
echo Starting Streamlit...
echo Open your browser to: http://localhost:8501
echo.

%VENV_PY% -m streamlit run src/app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo [ERROR] Something went wrong. Please scroll up for details.
pause
exit /b 1
