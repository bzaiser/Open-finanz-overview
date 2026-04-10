@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo   Finanzplan Dashboard - UNIVERSAL-START
echo ===========================================
echo.

set "DOWNLOAD_URL=https://github.com/bzaiser/Open-finanz-overview/archive/refs/heads/main.zip"
set "TARGET_DIR=Finanzplan-Dashboard"

if exist "%TARGET_DIR%" (
    echo [+] Programm bereits vorhanden.
    set /p UPDATE_CHOICE="Nach Updates suchen? (J/N): "
    if /i "!UPDATE_CHOICE!"=="J" goto DOWNLOAD
    goto START_APP
)

:DOWNLOAD
echo [+] Lade aktuelle Version...
powershell -command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile 'app.zip'"
echo [+] Entpacke Dateien...
powershell -command "Expand-Archive -Path 'app.zip' -DestinationPath 'temp_extract' -Force"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
for /d %%D in (temp_extract\*) do (
    echo [+] Aktualisiere Dateien...
    xcopy /E /I /Y /Q "%%D\*" "%TARGET_DIR%\"
)

rd /S /Q temp_extract
del "app.zip"

:SETUP_NATIVE
echo [+] Starte System-Pruefung...
set "ROOT_DIR=%CD%"
cd /d "%TARGET_DIR%"
if exist "native-dist\setup-native.bat" (
    call "native-dist\setup-native.bat"
) else (
    echo [FEHLER] Einrichtungsskript nicht gefunden!
    pause
    exit /b 1
)

REM --- PRIME 2.0 DESKTOP ICONS (ROBUST EDITION) ---
echo.
set /p ICON_CHOICE="Prime-Desktop-Icons erstellen? (J/N): "
if /i "!ICON_CHOICE!"=="J" (
    echo [+] Erstelle Premium-Verknuepfungen...
    REM Wir nutzen eine PowerShell-Variable für die Pfade, um Leerzeichen-Fehler zu vermeiden
    powershell -NoProfile -Command ^
        "$d = [Environment]::GetFolderPath('Desktop'); ^
         $ws = New-Object -ComObject WScript.Shell; ^
         $curr = (Get-Location).Path; ^
         $root = (Get-Item $curr).Parent.FullName; ^
         $s1 = $ws.CreateShortcut((Join-Path $d 'Finanzplan Dashboard.lnk')); ^
         $s1.TargetPath = (Join-Path $curr 'native-dist\start-dashboard.bat'); ^
         $s1.WorkingDirectory = (Join-Path $curr 'native-dist'); ^
         $s1.IconLocation = 'shell32.dll, 167'; ^
         $s1.Save(); ^
         $s2 = $ws.CreateShortcut((Join-Path $d 'Finanzplan Wartung.lnk')); ^
         $s2.TargetPath = (Join-Path $root 'Finanzplan-Mobil.bat'); ^
         $s2.WorkingDirectory = $root; ^
         $s2.IconLocation = 'shell32.dll, 71'; ^
         $s2.Save(); ^
         if ($?) { Write-Host '[+] Duo-Icons erfolgreich auf dem Desktop erstellt!' -ForegroundColor Green } else { Write-Host '[FEHLER] Konnte Icons nicht erstellen.' -ForegroundColor Red; pause }"
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"
exit /b 0
