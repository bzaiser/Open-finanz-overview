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
cd /d "%TARGET_DIR%"
if exist "native-dist\setup-native.bat" (
    call "native-dist\setup-native.bat"
) else (
    echo [FEHLER] Einrichtungsskript nicht gefunden!
    pause
    exit /b 1
)

REM --- PRIME 2.0 DESKTOP ICONS (SYSTEM-ICON EDITION) ---
echo.
set /p ICON_CHOICE="Prime-Desktop-Icons erstellen? (J/N): "
if /i "!ICON_CHOICE!"=="J" (
    echo [+] Erstelle Premium-Verknuepfungen...
    REM Wir nutzen shell32.dll Icons, da Windows keine PNGs in Verknuepfungen erlaubt. 
    REM 167 = Goldmuenze, 71 = Zahnrad
    powershell -NoProfile -Command "$d = [Environment]::GetFolderPath('Desktop'); $ws = New-Object -ComObject WScript.Shell; $s1 = $ws.CreateShortcut((Join-Path $d 'Finanzplan Dashboard.lnk')); $s1.TargetPath = '%CD%\native-dist\start-dashboard.bat'; $s1.WorkingDirectory = '%CD%\native-dist'; $s1.IconLocation = 'shell32.dll, 167'; $s1.Save(); $s2 = $ws.CreateShortcut((Join-Path $d 'Finanzplan Wartung.lnk')); $s2.TargetPath = '%CD%\..\Finanzplan-Mobil.bat'; $s2.WorkingDirectory = '%CD%\..'; $s2.IconLocation = 'shell32.dll, 71'; $s2.Save(); Write-Host '[+] Premium Duo-Icons erstellt!' -ForegroundColor Green"
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"
exit /b 0
