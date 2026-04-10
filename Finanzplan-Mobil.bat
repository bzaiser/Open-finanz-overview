@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Universal-Start
echo ==========================================
echo.
echo Dieses Skript laedt das Programm herunter 
echo und richtet alles fuer dich ein. 
echo Keine Installation notwendig!
echo.
pause

set "DOWNLOAD_URL=https://github.com/bzaiser/Open-finanz-overview/archive/refs/heads/main.zip"
set "TEMP_ZIP=app_download.zip"
set "TARGET_DIR=Finanzplan-Dashboard"
set "BACKUP_DIR=backup_temp"

if exist "%TARGET_DIR%" (
    echo [+] Programm-Ordner existiert bereits.
    echo [+] Moechtest du das Programm auf die neueste Version aktualisieren?
    echo [WICHTIG] Deine Datenbank und Einstellungen bleiben erhalten.
    set /p UPDATE_CHOICE="Aktualisieren? (J/N): "
    if /i "!UPDATE_CHOICE!"=="J" (
        echo [+] Erstelle Backup von Datenbank und Einstellungen...
        if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
        if exist "%TARGET_DIR%\db.sqlite3" copy /Y "%TARGET_DIR%\db.sqlite3" "%BACKUP_DIR%\"
        if exist "%TARGET_DIR%\.env" copy /Y "%TARGET_DIR%\.env" "%BACKUP_DIR%\"
        
        echo [+] Entferne alte Programm-Dateien...
        rd /S /Q "%TARGET_DIR%"
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
    xcopy /E /I /Y "%%D\*" "%TARGET_DIR%\"
)

echo [+] Aufraeumen...
rd /S /Q temp_extract
del "%TEMP_ZIP%"

REM Restore Backup if exists
if exist "%BACKUP_DIR%" (
    echo [+] Stelle Datenbank und Einstellungen wieder her...
    if exist "%BACKUP_DIR%\db.sqlite3" copy /Y "%BACKUP_DIR%\db.sqlite3" "%TARGET_DIR%\"
    if exist "%BACKUP_DIR%\.env" copy /Y "%BACKUP_DIR%\.env" "%TARGET_DIR%\"
    rd /S /Q "%BACKUP_DIR%"
)

:SETUP_NATIVE
echo [+] Starte System-Einrichtung (Python)...
cd /d "%TARGET_DIR%"
if exist "native-dist\setup-native.bat" (
    call "native-dist\setup-native.bat"
) else (
    echo [FEHLER] Einrichtungsskript nicht gefunden!
    pause
    exit /b 1
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"

exit /b 0
