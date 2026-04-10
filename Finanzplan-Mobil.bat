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

REM Icon-Check am Ende der Einrichtung
if exist "%USERPROFILE%\Desktop\Finanzplan Dashboard.lnk" goto START_APP
echo.
set /p ICON_CHOICE="Desktop-Icon erstellen? (J/N): "
if /i "!ICON_CHOICE!"=="J" (
    powershell -NoProfile -Command "$d = [Environment]::GetFolderPath('Desktop'); $s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Finanzplan Dashboard.lnk')); $s.TargetPath = '%CD%\%TARGET_DIR%\native-dist\start-dashboard.bat'; $s.WorkingDirectory = '%CD%\%TARGET_DIR%\native-dist'; $s.Save(); Write-Host '[+] Icon erstellt!' -ForegroundColor Green"
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"
exit /b 0
