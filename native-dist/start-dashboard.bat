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
echo [+] Pruefe Datenbank-Status...
"%PYTHON_EXE%" manage.py makemigrations --noinput >nul 2>&1
"%PYTHON_EXE%" manage.py migrate --noinput >nul 2>&1
"%PYTHON_EXE%" manage.py createcachetable >nul 2>&1

REM Intelligente Prüfung: Existiert der Demo-Nutzer?
"%PYTHON_EXE%" manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('USER_OK' if User.objects.filter(username='demo').exists() else 'USER_MISSING')" | findstr "USER_MISSING" > nul
if %errorlevel% equ 0 (
    echo [+] Demo-Benutzer fehlt oder Datenbank leer. Erstelle Demo-Daten...
    "%PYTHON_EXE%" manage.py seed_portable
)

:COLLECT
echo [+] Bereite statische Dateien vor...
"%PYTHON_EXE%" manage.py collectstatic --noinput >nul 2>&1

cls
echo ============================================================
echo   FINANZPLAN DASHBOARD - AKTIV
echo ============================================================
echo.
echo   Der Server ist jetzt unter folgender Adresse erreichbar:
echo.
echo           ---  http://localhost:8000  ---
echo.
echo   ----------------------------------------------------------
echo   BEDIENUNGSHINWEIS:
echo   [!] Du kannst dieses Fenster jetzt MINIMIEREN.
echo   [!] Zum BEENDEN: Druecke 2x STRG+C oder schliesse dieses Fenster.
echo   ----------------------------------------------------------
echo.

REM Browser-Start
start "" http://localhost:8000

REM Waitress Start
"%PYTHON_EXE%" -m waitress --port=8000 --threads=12 config.wsgi:application

pause
