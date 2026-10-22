@echo off
rem Windows: double-click. Starts the application window without a black console window.
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 run.pyw & exit /b)
where pythonw >nul 2>nul && (start "" pythonw run.pyw & exit /b)
echo Python 3.9 or newer was not found. Install it from https://www.python.org/downloads/ ^(tick "Add Python to PATH"^) and start this file again.
pause
