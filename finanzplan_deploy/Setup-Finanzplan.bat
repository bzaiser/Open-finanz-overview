@echo off
setlocal

echo ==========================================
echo   Finanzplan Dashboard - Setup Assistent
echo ==========================================
echo.

:: 1. Check for Git
where git >nul 2>nul
    echo [+] Git wurde nicht gefunden. Starte Installation via winget...
    winget install --id Git.Git -e --source winget --silent --accept-source-agreements --accept-package-agreements
    
    :: Wir ignorieren hier den Exit-Code von winget, da es oft "fehlschlägt", 
    :: wenn Git bereits installiert aber nicht im PATH ist (z.B. "Kein Update verfügbar").
    
    echo [+] Aktualisiere PATH für diese Sitzung...
    set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
    
    :: Jetzt prüfen wir erneut, ob git erkannt wird
    where git >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [INFO] Git konnte nicht automatisch konfiguriert werden. 
        echo Bitte installiere Git manuell von https://git-scm.com/ oder starte den Terminal neu.
        pause
        exit /b 0
    )
    echo [+] Git erfolgreich erkannt. Weiter geht's...
)

:: 2. Clone the Repository
if not exist finanzplan (
    echo [+] Klone Repository 'Open-finanz-overview' von GitHub...
    git clone https://github.com/bzaiser/Open-finanz-overview.git finanzplan
    if %ERRORLEVEL% neq 0 (
        echo [FEHLER] Klonen fehlgeschlagen!
        pause
        exit /b 1
    )
) else (
    echo [+] Ordner 'finanzplan' existiert bereits.
)

:: 3. Handover to internal start script
echo [+] Starte Dashboard-Setup...
cd finanzplan
if exist portable-dist\start-windows.bat (
    call portable-dist\start-windows.bat
) else (
    echo [FEHLER] Start-Skript nicht gefunden in: finanzplan\portable-dist\start-windows.bat
    pause
)

exit /b 0
