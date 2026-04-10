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
    echo [WICHTIG] Deine Datenbank, Einstellungen und Python bleiben erhalten.
    set /p UPDATE_CHOICE="Aktualisieren? (J/N): "
    if /i "!UPDATE_CHOICE!"=="J" (
        echo [+] Erstelle Backup von Datenbank, Einstellungen und Python...
        if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
        if exist "%TARGET_DIR%\db.sqlite3" move /Y "%TARGET_DIR%\db.sqlite3" "%BACKUP_DIR%\"
        if exist "%TARGET_DIR%\.env" move /Y "%TARGET_DIR%\.env" "%BACKUP_DIR%\"
        
        REM Python-Ordner sichern, damit er nicht neu geladen werden muss
        if exist "%TARGET_DIR%\native-dist\python-embed" (
            echo [+] Parke Python-Umgebung zwischen...
            move /Y "%TARGET_DIR%\native-dist\python-embed" "%BACKUP_DIR%\"
        )
        
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
    echo [+] Stelle Datenbank, Einstellungen und Python wieder her...
    if exist "%BACKUP_DIR%\db.sqlite3" move /Y "%BACKUP_DIR%\db.sqlite3" "%TARGET_DIR%\"
    if exist "%BACKUP_DIR%\.env" move /Y "%BACKUP_DIR%\.env" "%TARGET_DIR%\"
    
    REM Python zurückbewegen
    if exist "%BACKUP_DIR%\python-embed" (
        if not exist "%TARGET_DIR%\native-dist" mkdir "%TARGET_DIR%\native-dist"
        move /Y "%BACKUP_DIR%\python-embed" "%TARGET_DIR%\native-dist\"
    )
    
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

REM DEKSTOP VERKNÜPFUNG ERSTELLEN
echo.
set /p SHORTCUT_CHOICE="Moechtest du eine Verknuepfung auf dem Desktop erstellen? (J/N): "
if /i "!SHORTCUT_CHOICE!"=="J" (
    echo [+] Erstelle Desktop-Verknuepfung...
    powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Finanzplan Dashboard.lnk'));$s.TargetPath='%CD%\Finanzplan-Mobil.bat';$s.WorkingDirectory='%CD%';$s.Save()"
    echo [+] Verknuepfung erstellt!
)

:START_APP
echo [+] Starte Dashboard...
cd /d "%TARGET_DIR%"
call "native-dist\start-dashboard.bat"

exit /b 0
