@echo off
setlocal

echo ==========================================
echo   Finanzplan Dashboard - Setup Assistent
echo ==========================================
echo.

REM 1. Check for Git
where git >nul 2>nul
if %ERRORLEVEL% equ 0 goto GIT_OK

REM Notsuche an Standard-Orten
if exist "C:\Program Files\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files\Git\cmd"
where git >nul 2>nul
if %ERRORLEVEL% equ 0 goto GIT_OK

echo [+] Git wurde nicht gefunden. Starte Installation via winget...
winget install --id Git.Git -e --source winget --silent --accept-source-agreements --accept-package-agreements

REM Pfad fuer diese Sitzung aktualisieren
set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"

where git >nul 2>nul
if %ERRORLEVEL% equ 0 goto GIT_OK

if exist "C:\Program Files\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files\Git\cmd"
where git >nul 2>nul
if %ERRORLEVEL% equ 0 goto GIT_OK

echo.
echo [INFO] Git konnte nicht automatisch konfiguriert werden.
pause
exit /b 0

:GIT_OK
echo [+] Git erfolgreich erkannt. Weiter geht's...

REM 2. Clone the Repository
if exist "Open-finanz-overview" goto UPDATE_REPO

echo [+] Klone Repository 'Open-finanz-overview' von GitHub...
git clone "https://github.com/bzaiser/Open-finanz-overview.git"
if %ERRORLEVEL% neq 0 goto CLONE_ERROR
goto HANDOVER

:UPDATE_REPO
echo [+] Ordner 'Open-finanz-overview' existiert bereits. Suche nach Updates...
cd "Open-finanz-overview"
git pull
cd ..
goto HANDOVER

:CLONE_ERROR
echo [FEHLER] Klonen fehlgeschlagen!
pause
exit /b 1

:HANDOVER
REM 3. Handover to internal start script
echo [+] Starte Dashboard-Setup...
if not exist "Open-finanz-overview\portable-dist\start-windows.bat" goto MISSING_START
cd "Open-finanz-overview"
call "portable-dist\start-windows.bat"
exit /b 0

:MISSING_START
echo [FEHLER] Start-Skript nicht gefunden!
pause
exit /b 1
