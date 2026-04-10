@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Portable Setup
echo ==========================================
echo.

REM --- DETECTION ---
set DOCKER_CMD=podman

REM 1. Pruefe ob podman bereits im PATH ist
where podman >nul 2>nul
if %ERRORLEVEL% equ 0 goto AUTO_MACHINE

REM 2. Suche an Standard-Orten fuer podman.exe
if exist "C:\Program Files\RedHat\Podman\podman.exe" (
    set DOCKER_CMD="C:\Program Files\RedHat\Podman\podman.exe"
    goto AUTO_MACHINE
)
if exist "C:\Program Files\Podman Desktop\podman.exe" (
    set DOCKER_CMD="C:\Program Files\Podman Desktop\podman.exe"
    goto AUTO_MACHINE
)
if exist "%LOCALAPPDATA%\Programs\Podman Desktop\podman.exe" (
    set DOCKER_CMD="%LOCALAPPDATA%\Programs\Podman Desktop\podman.exe"
    goto AUTO_MACHINE
)

REM 3. Fallback auf Docker, falls kein Podman gefunden wurde
where docker >nul 2>nul
if %ERRORLEVEL% equ 0 set DOCKER_CMD=docker
if %ERRORLEVEL% equ 0 goto CHECK_ENV

REM --- INSTALLATION ASSISTANT ---
echo [INFO] Weder Podman noch Docker wurden auf deinem System gefunden.
echo Dies ist fuer den Betrieb des Dashboards notwendig.
echo.
echo Wie moechtest du fortfahren?
echo [1] Podman (Engine + Desktop GUI) installieren (Empfohlen)
echo [2] Docker Desktop installieren (Kommerziell/Enterprise)
echo [3] Beenden und manuell installieren
echo.
set /p INSTALL_CHOICE="Waehle eine Option [1-3]: "

if "%INSTALL_CHOICE%"=="1" goto INSTALL_PODMAN
if "%INSTALL_CHOICE%"=="2" goto INSTALL_DOCKER
if "%INSTALL_CHOICE%"=="3" goto EXIT_MANUAL
goto CHECK_ENV

:INSTALL_PODMAN
echo.
echo ============================================================
echo   WICHTIG: Es erscheinen gleich 1-2 Windows-Abfragen (Admin)
echo   fuer die Installation von Podman.
echo.
echo   Bitte bestaetige diese, damit die Installation 
echo   abgeschlossen werden kann.
echo ============================================================
echo.
pause
echo [+] Starte Installation von Podman Engine (CLI) via winget...
winget install --id RedHat.Podman -e --source winget --silent --accept-source-agreements --accept-package-agreements

echo [+] Starte Installation von Podman Desktop (GUI) via winget...
winget install --id RedHat.Podman-Desktop -e --source winget --silent --accept-source-agreements --accept-package-agreements

REM Pfad nach Installation erzwingen und absolut setzen
if exist "C:\Program Files\RedHat\Podman\podman.exe" set DOCKER_CMD="C:\Program Files\RedHat\Podman\podman.exe"
goto AUTO_MACHINE

:INSTALL_DOCKER
echo.
echo ============================================================
echo   WICHTIG: Es erscheint gleich eine Windows-Abfrage (Admin)
echo   fuer die Installation von Docker Desktop.
echo.
echo   Bitte bestaetige diese, damit die Installation 
echo   abgeschlossen werden kann.
echo ============================================================
echo.
pause
echo [+] Starte Installation von Docker Desktop via winget...
winget install -e --id Docker.DockerDesktop
goto AFTER_INSTALL

:EXIT_MANUAL
echo.
echo Bitte lade eine der folgenden Applikationen herunter:
echo Podman Desktop: https://podman-desktop.io/
echo Docker Desktop: https://www.docker.com/products/docker-desktop/
echo.
pause
exit /b 0

:AFTER_INSTALL
echo.
echo ============================================================
echo   WICHTIG: Bitte starte das gerade installierte Programm 
echo   (Podman oder Docker) jetzt manuell und schliesse die 
echo   Ersteinrichtung (z.B. Erstellen einer Machine) ab.
echo.
echo   Sobald das Programm laeuft, starte dieses Skript erneut.
echo ============================================================
pause
exit /b 0

:AUTO_MACHINE
REM --- PODMAN MACHINE AUTO-START ---
if not "%DOCKER_CMD%"=="docker" goto PODMAN_INIT

goto CHECK_ENV

:PODMAN_INIT
echo [+] Pruefe Podman Maschine...

REM Nutze den absoluten Befehl fuer alle Podman Aktionen
%DOCKER_CMD% machine list --format "{{.Name}}" | findstr /r "." >nul
if %ERRORLEVEL% equ 0 goto START_MACHINE

echo [+] Keine Podman Maschine gefunden. Initialisiere (dies dauert einen Moment)...
%DOCKER_CMD% machine init --cpus 2 --memory 2048
if %ERRORLEVEL% neq 0 goto INIT_ERROR
goto START_MACHINE

:INIT_ERROR
echo [FEHLER] Podman Machine konnte nicht initialisiert werden. 
echo Ist WSL2 installiert? (winget install Microsoft.WSL)
pause
exit /b 1

:START_MACHINE
%DOCKER_CMD% machine list --format "{{.LastUp}}" | findstr /i "Currently" >nul
if %ERRORLEVEL% equ 0 goto CHECK_ENV

echo [+] Podman Maschine ist gestoppt. Starte Maschine...
%DOCKER_CMD% machine start
if %ERRORLEVEL% neq 0 goto START_ERROR
echo [+] Warte auf Maschinenzustand...
timeout /t 5 /nobreak >nul
goto CHECK_ENV

:START_ERROR
echo [FEHLER] Podman Machine konnte nicht gestartet werden.
pause
exit /b 1

:CHECK_ENV
set NEW_INSTALL=0
if exist .env goto LOAD_ENV

set NEW_INSTALL=1
echo [+] Erster Start erkannt: Starte Setup-Assistent...
echo.
    
REM 1. PORT
set /p WEB_PORT="Welchen Port soll das Dashboard nutzen? [Standard: 8000]: "
if "!WEB_PORT!"=="" set WEB_PORT=8000
    
REM 2. INSTANCE NAME
set /p APP_INSTANCE_NAME="Wie soll deine Instanz heissen? (z.B. Privat) [Standard: Private]: "
if "!APP_INSTANCE_NAME!"=="" set APP_INSTANCE_NAME=Private
    
REM 3. AI PROVIDER
echo.
echo Welchen KI-Assistenten moechtest du nutzen?
echo [1] Keinen (Standard)
echo [2] Ollama (Lokal, setzt installierten Ollama-Server voraus)
echo [3] Groq (Cloud, sehr schnell, erfordert API-Key)
set /p AI_CHOICE="Waehle eine Option [1-3]: "
    
set LLM_PROVIDER=none
set OLLAMA_URL=http://localhost:11434
set GROQ_KEY=
    
if "!AI_CHOICE!"=="2" set LLM_PROVIDER=ollama
if "!AI_CHOICE!"=="3" set LLM_PROVIDER=groq

if "!LLM_PROVIDER!"=="ollama" (
    set /p OLLAMA_URL="Ollama URL [Standard: http://localhost:11434]: "
    if "!OLLAMA_URL!"=="" set OLLAMA_URL=http://localhost:11434
)
if "!LLM_PROVIDER!"=="groq" (
    set /p GROQ_KEY="Bitte gib deinen Groq API-Key ein: "
)

REM Write .env file
echo # Automatisch generiert durch Setup-Assistent > .env
echo WEB_PORT=!WEB_PORT! >> .env
echo APP_INSTANCE_NAME=!APP_INSTANCE_NAME! >> .env
echo LLM_PROVIDER=!LLM_PROVIDER! >> .env
echo OLLAMA_BASE_URL=!OLLAMA_URL! >> .env
echo GROQ_API_KEY=!GROQ_KEY! >> .env
echo DEBUG=False >> .env
echo ALLOWED_HOSTS=* >> .env
echo RUNNING_IN_DOCKER=1 >> .env
echo SECRET_KEY=portable_!RANDOM!_!RANDOM! >> .env
    
echo.
echo [+] Setup abgeschlossen! .env wurde erstellt.
echo.
goto DB_CHECK

:LOAD_ENV
REM Load WEB_PORT from .env if it exists
for /f "tokens=2 delims==" %%a in ('findstr "WEB_PORT" .env') do set WEB_PORT=%%a

:DB_CHECK
REM Ensure db.sqlite3 is a file
if exist db.sqlite3 goto COMPOSE_UP
set NEW_INSTALL=1
echo [+] Initialisiere Datenbank-Datei...
type nul > db.sqlite3

:COMPOSE_UP
REM Start the containers
echo [+] Nutze %DOCKER_CMD% fuer den Start...
%DOCKER_CMD% compose up -d

if %ERRORLEVEL% neq 0 goto UP_ERROR
if %NEW_INSTALL% equ 1 goto SEED_DATA
goto FINISH

:UP_ERROR
echo [FEHLER] Der Start ist fehlgeschlagen!
pause
exit /b 1

:SEED_DATA
echo [+] Erster Start erkannt: Erstelle Datenbank-Tabellen...
%DOCKER_CMD% exec finanzplan-portable python manage.py migrate --noinput
echo [+] Befuelle Datenbank mit Demo-Daten (User: demo / demo)...
%DOCKER_CMD% exec finanzplan-portable python manage.py seed_portable --noinput

:FINISH
echo.
echo URL: http://localhost:%WEB_PORT%
echo Login: demo / demo
echo.

REM Open browser after a small delay
timeout /t 5 /nobreak >nul
start http://localhost:%WEB_PORT%

echo ==========================================
echo   FERTIG! Das Dashboard laeuft.
echo ==========================================
pause
