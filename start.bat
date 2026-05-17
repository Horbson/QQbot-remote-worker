@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Virtual environment not found: %PYTHON%
    echo Please run: python -m venv .venv
    echo Then run: .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

"%PYTHON%" "%ROOT%app.py"
pause
