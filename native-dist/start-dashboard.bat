@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Launcher
echo ==========================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "PYTHON_DIR=%~dp0python-embed"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [FEHLER] Python Umgebung nicht gefunden.
    echo Bitte starte zuerst 'setup-native.bat'.
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

REM Check for .env file
if not exist ".env" (
    echo [+] Erster Start: Generiere Standard-Konfiguration...
    echo DEBUG=False > .env
    echo ALLOWED_HOST_NAME=localhost >> .env
    echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
    echo SECRET_KEY=native_!RANDOM!_!RANDOM! >> .env
)

echo [+] Pruefe Datenbank-Migrationen...
"%PYTHON_EXE%" manage.py migrate --noinput

echo [+] Bereite statische Dateien vor...
"%PYTHON_EXE%" manage.py collectstatic --noinput

echo [+] Starte Webserver (Waitress) auf Port 8000...
echo     Das Dashboard ist gleich unter http://localhost:8000 erreichbar.
echo.

REM Open browser after a small delay
start "" http://localhost:8000

REM Launch the server
"%PYTHON_EXE%" -m waitress --port=8000 config.wsgi:application

pause
