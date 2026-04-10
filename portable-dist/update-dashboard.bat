@echo off
setlocal

echo ==========================================
echo   Finanzplan Dashboard - Update Assistent
echo ==========================================
echo.

:: Check for Git
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [FEHLER] Git wurde nicht gefunden. Update nicht moeglich.
    pause
    exit /b 1
)

:: Pull latest changes
echo [+] Suche nach Updates auf GitHub...
cd ..
git pull
if %ERRORLEVEL% neq 0 (
    echo [FEHLER] Git Pull fehlgeschlagen. Bitte Internetverbindung pruefen.
    cd portable-dist
    pause
    exit /b 1
)
cd portable-dist

:: Rebuild and restart
echo [+] Baue Container neu und starte...
for /f "tokens=2 delims==" %%a in ('findstr "DOCKER_CMD" start-windows.bat') do set DOCKER_CMD=%%a
if "%DOCKER_CMD%"=="" set DOCKER_CMD=podman
where %DOCKER_CMD% >nul 2>nul
if %ERRORLEVEL% neq 0 set DOCKER_CMD=docker

%DOCKER_CMD% compose up -d --build

if %ERRORLEVEL% neq 0 (
    echo [FEHLER] Rebuild fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   UPDATE ERFOLGREICH!
echo ==========================================
pause
