@echo off
setlocal
cd /d "%~dp0"
python base_sap_workspace.py
if errorlevel 1 (
  echo Check Python and dependencies. Install with:
  echo python -m pip install -r requirements.txt
)
pause
