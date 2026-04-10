@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Launcher
echo ==========================================
echo.

set "NATIVE_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0.."
set "PYTHON_DIR=%~dp0python-embed"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [FEHLER] Python Umgebung nicht gefunden.
    echo Bitte starte zuerst 'setup-native.bat'.
    pause
    exit /b 1
)

REM --- LIVE PFAD FIX ---
REM Wir ermitteln den absoluten Pfad zum Projekt-Root
pushd "%PROJECT_ROOT%"
set "ABS_ROOT=%CD%"
popd

REM Wir aktualisieren die ._pth Datei dynamisch mit dem absoluten Pfad. 
REM Das stellt sicher, dass Python 'config' immer findet, egal wo der Ordner liegt.
for %%f in ("%PYTHON_DIR%\python3*._pth") do (
    for %%i in ("%PYTHON_DIR%\python3*.zip") do set "ZIP_NAME=%%~nxi"
    echo !ZIP_NAME!> "%%f"
    echo .>> "%%f"
    echo !ABS_ROOT!>> "%%f"
    echo import site>> "%%f"
)
REM ---------------------

cd /d "%PROJECT_ROOT%"

REM Check for .env file
set "NEW_INSTALL=0"
if not exist ".env" (
    set "NEW_INSTALL=1"
    echo [+] Erster Start: Generiere Standard-Konfiguration...
    echo DEBUG=False > .env
    echo ALLOWED_HOST_NAME=localhost >> .env
    echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
    echo SECRET_KEY=native_!RANDOM!_!RANDOM! >> .env
)

REM Check if database exists
if not exist "db.sqlite3" set "NEW_INSTALL=1"

echo [+] Pruefe Datenbank-Migrationen...
"%PYTHON_EXE%" manage.py migrate --noinput

if "!NEW_INSTALL!"=="1" (
    echo [+] Initial-Setup: Erstelle Demo-Daten (User: demo / demo)...
    "%PYTHON_EXE%" manage.py seed_portable --noinput
)

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
