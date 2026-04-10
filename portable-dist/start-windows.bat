@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Portable Setup
echo ==========================================
echo.

:: Check for Podman first, then Docker
where podman >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set DOCKER_CMD=podman
    goto AUTO_MACHINE
) else (
    :: Fallback: Check if Podman is installed in standard path but not in PATH yet
    if exist "C:\Program Files\RedHat\Podman\podman.exe" (
        echo [INFO] Podman im Standardpfad gefunden. Aktualisiere PATH...
        set "PATH=%PATH%;C:\Program Files\RedHat\Podman"
        set DOCKER_CMD=podman
        goto AUTO_MACHINE
    )
)

where docker >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set DOCKER_CMD=docker
    goto CHECK_ENV
)

:: --- INSTALLATION ASSISTANT ---
echo [INFO] Weder Podman noch Docker wurden auf deinem System gefunden.
echo Dies ist fuer den Betrieb des Dashboards notwendig.
echo.
echo Wie moechtest du fortfahren?
echo [1] Podman Desktop installieren (Empfohlen, Open Source)
echo [2] Docker Desktop installieren (Kommerziell/Enterprise)
echo [3] Beenden und manuell installieren
echo.
set /p INSTALL_CHOICE="Waehle eine Option [1-3]: "

if "%INSTALL_CHOICE%"=="1" (
    echo [+] Starte Installation von Podman via winget...
    winget install --id RedHat.Podman -e --source winget --silent --accept-source-agreements --accept-package-agreements
    
    echo [+] Aktualisiere PATH für Podman...
    set "PATH=%PATH%;C:\Program Files\RedHat\Podman"
    set DOCKER_CMD=podman
    goto AUTO_MACHINE
)
if "%INSTALL_CHOICE%"=="2" (
    echo [+] Starte Installation von Docker Desktop via winget...
    winget install -e --id Docker.DockerDesktop
    goto AFTER_INSTALL
)
if "%INSTALL_CHOICE%"=="3" (
    echo.
    echo Bitte lade eine der folgenden Applikationen herunter:
    echo Podman Desktop: https://podman-desktop.io/
    echo Docker Desktop: https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 0
)
goto CHECK_ENV

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
:: --- PODMAN MACHINE AUTO-START ---
if "%DOCKER_CMD%"=="podman" (
    echo [+] Pruefe Podman Maschine...
    podman --version >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [INFO] Podman CLI noch nicht erkannt. Versuche PATH Refresh...
        set "PATH=%PATH%;C:\Program Files\RedHat\Podman"
    )

    %DOCKER_CMD% machine list --format "{{.Name}}" | findstr /r "." >nul
    if %ERRORLEVEL% neq 0 (
        echo [+] Keine Podman Maschine gefunden. Initialisiere (dies dauert einen Moment)...
        %DOCKER_CMD% machine init --cpus 2 --memory 2048
        if %ERRORLEVEL% neq 0 (
            echo [FEHLER] Podman Machine konnte nicht initialisiert werden. 
            echo Ist WSL2 installiert? (winget install Microsoft.WSL)
            pause
            exit /b 1
        )
    )
    
    %DOCKER_CMD% machine list --format "{{.LastUp}}" | findstr /i "Currently" >nul
    if %ERRORLEVEL% neq 0 (
        echo [+] Podman Maschine ist gestoppt. Starte Maschine...
        %DOCKER_CMD% machine start
        if %ERRORLEVEL% neq 0 (
            echo [FEHLER] Podman Machine konnte nicht gestartet werden.
            pause
            exit /b 1
        )
        echo [+] Warte auf Maschinenzustand...
        timeout /t 5 /nobreak >nul
    )
)

:CHECK_ENV
set NEW_INSTALL=0
if not exist .env (
    set NEW_INSTALL=1
    echo [+] Erster Start erkannt: Starte Setup-Assistent...
    echo.
    
    :: 1. PORT
    set /p WEB_PORT="Welchen Port soll das Dashboard nutzen? [Standard: 8000]: "
    if "!WEB_PORT!"=="" set WEB_PORT=8000
    
    :: 2. INSTANCE NAME
    set /p APP_INSTANCE_NAME="Wie soll deine Instanz heissen? (z.B. Privat) [Standard: Private]: "
    if "!APP_INSTANCE_NAME!"=="" set APP_INSTANCE_NAME=Private
    
    :: 3. AI PROVIDER
    echo.
    echo Welchen KI-Assistenten moechtest du nutzen?
    echo [1] Keinen (Standard)
    echo [2] Ollama (Lokal, setzt installierten Ollama-Server voraus)
    echo [3] Groq (Cloud, sehr schnell, erfordert API-Key)
    set /p AI_CHOICE="Waehle eine Option [1-3]: "
    
    set LLM_PROVIDER=none
    set OLLAMA_URL=http://localhost:11434
    set GROQ_KEY=
    
    if "!AI_CHOICE!"=="2" (
        set LLM_PROVIDER=ollama
        set /p OLLAMA_URL="Ollama URL [Standard: http://localhost:11434]: "
        if "!OLLAMA_URL!"=="" set OLLAMA_URL=http://localhost:11434
    )
    if "!AI_CHOICE!"=="3" (
        set LLM_PROVIDER=groq
        set /p GROQ_KEY="Bitte gib deinen Groq API-Key ein: "
    )

    :: Write .env file
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
) else (
    :: Load WEB_PORT from .env if it exists
    for /f "tokens=2 delims==" %%a in ('findstr "WEB_PORT" .env') do set WEB_PORT=%%a
)

:: Ensure db.sqlite3 is a file
if not exist db.sqlite3 (
    set NEW_INSTALL=1
    echo [+] Initialisiere Datenbank-Datei...
    type nul > db.sqlite3
)

:: Start the containers
echo [+] Nutze %DOCKER_CMD% fuer den Start...
%DOCKER_CMD% compose up -d

if %ERRORLEVEL% neq 0 (
    echo [FEHLER] Der Start ist fehlgeschlagen!
    pause
    exit /b 1
)

:: Run migrations and seed data on fresh install
if %NEW_INSTALL% equ 1 (
    echo [+] Erster Start erkannt: Erstelle Datenbank-Tabellen...
    %DOCKER_CMD% exec finanzplan-portable python manage.py migrate --noinput
    echo [+] Befuelle Datenbank mit Demo-Daten (User: demo / demo)...
    %DOCKER_CMD% exec finanzplan-portable python manage.py seed_portable --noinput
)

echo.
echo URL: http://localhost:%WEB_PORT%
echo Login: demo / demo
echo.

:: Open browser after a small delay
timeout /t 5 /nobreak >nul
start http://localhost:%WEB_PORT%

echo ==========================================
echo   FERTIG! Das Dashboard laeuft.
echo ==========================================
pause
