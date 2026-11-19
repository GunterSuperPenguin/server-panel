@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || exit /b 1

if not exist ".venv\pyvenv.cfg" goto create_venv
if not exist ".venv\Scripts\python.exe" goto create_venv
if not exist ".venv\Scripts\activate.bat" goto create_venv
goto setup

:create_venv
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv || goto failed
    goto setup
)
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 or newer is required. 1>&2
    goto failed
)
python -m venv .venv || goto failed

:setup
call ".venv\Scripts\activate.bat" || goto failed
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m ensurepip --upgrade || goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade --upgrade-strategy eager -e . || goto failed
".venv\Scripts\python.exe" -m panel
set "exit_code=%errorlevel%"
popd
exit /b %exit_code%

:failed
popd
exit /b 1
