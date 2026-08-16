@echo off
setlocal

cd /d "%~dp0"

echo Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 (
    echo Migration failed. Aborting.
    pause
    exit /b 1
)

echo Starting CIPLog server at http://127.0.0.1:8000/
start "" http://127.0.0.1:8000/
".venv\Scripts\python.exe" manage.py runserver

pause
