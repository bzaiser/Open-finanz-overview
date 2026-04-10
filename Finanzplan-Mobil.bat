@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Universal-Start
echo ==========================================
echo.
echo Dieses Skript laedt das Programm herunter 
echo und richtet alles fuer dich ein. 
echo.
pause

set "DOWNLOAD_URL=https://github.com/bzaiser/Open-finanz-overview/archive/refs/heads/main.zip"
set "TEMP_ZIP=app_download.zip"
set "TARGET_DIR=Finanzplan-Dashboard"

if exist "%TARGET_DIR%" (
    echo [+] Programm-Ordner existiert bereits.
    echo [+] Moechtest du nach Programm-Updates suchen?
    echo [WICHTIG] Deine Datenbank und Python bleiben dabei erhalten.
    set /p UPDATE_CHOICE="Aktualisieren? (J/N): "
    if /i "!UPDATE_CHOICE!"=="J" (
        goto DOWNLOAD
    )
    goto START_APP
)

:DOWNLOAD
echo [+] Lade Programm-Paket herunter...
powershell -command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TEMP_ZIP%'"

echo [+] Entpacke Dateien...
powershell -command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath 'temp_extract' -Force"

REM GitHub ZIPs haben einen Unterordner (z.B. Open-finanz-overview-main)
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
for /d %%D in (temp_extract\*) do (
    echo [+] Kopiere neue Dateien (ueberschreiben)...
    xcopy /E /I /Y /Q "%%D\*" "%TARGET_DIR%\"
)

echo [+] Aufraeumen...
rd /S /Q temp_extract
del "%TEMP_ZIP%"

:SETUP_NATIVE
echo [+] Starte System-Pruefung...
cd /d "%TARGET_DIR%"
if exist "native-dist\setup-native.bat" (
    call "native-dist\setup-native.bat"
) else (
    echo [FEHLER] Einrichtungsskript nicht gefunden!
    pause
    exit /b 1
)

REM DESKTOP VERKNÜPFUNG ERSTELLEN
if exist "%USERPROFILE%\Desktop\Finanzplan Dashboard.lnk" goto START_APP
echo.
set /p SHORTCUT_CHOICE="Moechtest du eine Verknuepfung auf dem Desktop erstellen? (J/N): "
if /i "!SHORTCUT_CHOICE!"=="J" (
    echo [+] Erstelle Desktop-Verknuepfung...
    powershell -NoProfile -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $path = Join-Path $desktop 'Finanzplan Dashboard.lnk'; $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut($path); $s.TargetPath = '%CD%\native-dist\start-dashboard.bat'; $s.WorkingDirectory = '%CD%\native-dist'; $s.IconLocation = '%CD%\native-dist\logo-prime.png'; $s.Save(); if ($?) { Write-Host 'Schnellstart-Icon erstellt!' -ForegroundColor Green } else { Write-Host 'Fehler beim Erstellen der Verknuepfung!' -ForegroundColor Red; pause }"
    echo.
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"

exit /b 0
