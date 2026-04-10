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
pushd "%PROJECT_ROOT%"
set "ABS_ROOT=%CD%"
popd

for %%f in ("%PYTHON_DIR%\python3*._pth") do (
    set "PTH_FILE=%%f"
    for %%i in ("%PYTHON_DIR%\python3*.zip") do set "ZIP_NAME=%%~nxi"
    echo !ZIP_NAME!> "!PTH_FILE!"
    echo .>> "!PTH_FILE!"
    echo !ABS_ROOT!>> "!PTH_FILE!"
    echo import site>> "!PTH_FILE!"
)

cd /d "%PROJECT_ROOT%"

REM Standard-Konfiguration falls .env fehlt
if exist ".env" goto CHECK_DB
echo [+] Erster Start: Generiere Standard-Konfiguration...
echo DEBUG=False > .env
echo ALLOWED_HOST_NAME=localhost >> .env
echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
echo SECRET_KEY=native_!RANDOM!_!RANDOM! >> .env

:CHECK_DB
set "NEW_INSTALL=0"
if not exist "db.sqlite3" set "NEW_INSTALL=1"

echo [+] Pruefe Datenbank-Migrationen...
"%PYTHON_EXE%" manage.py migrate --noinput

if "!NEW_INSTALL!"=="0" goto COLLECT
echo [+] Initial-Setup: Erstelle Demo-Daten (User: demo / demo)...
"%PYTHON_EXE%" manage.py seed_portable --noinput

:COLLECT
echo [+] Bereite statische Dateien vor...
"%PYTHON_EXE%" manage.py collectstatic --noinput

echo [+] Starte Webserver (Waitress) auf Port 8000...
echo     Das Dashboard ist gleich unter http://localhost:8000 erreichbar.
echo.

REM Browser-Start
start "" http://localhost:8000

REM Waitress Start
"%PYTHON_EXE%" -m waitress --port=8000 config.wsgi:application

pause
