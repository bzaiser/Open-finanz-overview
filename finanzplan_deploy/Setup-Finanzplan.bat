@echo off
setlocal

echo ==========================================
echo   Finanzplan Dashboard - Setup Assistent
echo ==========================================
echo.

REM 1. Check for Git
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    REM Notsuche an Standard-Orten
    if exist "C:\Program Files\Git\cmd\git.exe" (
        set "PATH=%PATH%;C:\Program Files\Git\cmd"
        goto GIT_OK
    )
    
    echo [+] Git wurde nicht gefunden. Starte Installation via winget...
    winget install --id Git.Git -e --source winget --silent --accept-source-agreements --accept-package-agreements
    
    echo [+] Aktualisiere PATH fuer diese Sitzung...
    set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
    
    where git >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        if exist "C:\Program Files\Git\cmd\git.exe" (
            set "PATH=%PATH%;C:\Program Files\Git\cmd"
            goto GIT_OK
        )
        echo.
        echo [INFO] Git konnte nicht automatisch konfiguriert werden. 
        echo Bitte installiere Git manuell von https://git-scm.com/ oder starte den Terminal neu.
        pause
        exit /b 0
    )
)

:GIT_OK
echo [+] Git erfolgreich erkannt. Weiter geht's...

REM 2. Clone the Repository
if not exist "Open-finanz-overview" (
    echo [+] Klone Repository 'Open-finanz-overview' von GitHub...
    git clone "https://github.com/bzaiser/Open-finanz-overview.git"
    if %ERRORLEVEL% neq 0 (
        echo [FEHLER] Klonen fehlgeschlagen!
        pause
        exit /b 1
    )
) else (
    echo [+] Ordner 'Open-finanz-overview' existiert bereits. Suche nach Updates...
    cd "Open-finanz-overview"
    git pull
    cd ..
)

REM 3. Handover to internal start script
echo [+] Starte Dashboard-Setup...
if exist "Open-finanz-overview\portable-dist\start-windows.bat" (
    cd "Open-finanz-overview"
    call "portable-dist\start-windows.bat"
) else (
    echo [FEHLER] Start-Skript nicht gefunden!
    pause
)

exit /b 0
