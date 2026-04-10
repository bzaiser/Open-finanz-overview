@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Finanzplan Dashboard - Native Setup
echo ==========================================
echo.
echo Dieses Skript konfiguriert eine isolierte 
echo Python-Umgebung in diesem Ordner.
echo Es werden ca. 30MB heruntergeladen.
echo.
pause

REM Absolute Pfade aufloesen
pushd "%~dp0.."
set "PROJECT_ROOT=%CD%"
popd
set "NATIVE_DIR=%~dp0"
set "PYTHON_DIR=%~dp0python-embed"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "PYTHON_ZIP_URL=https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip"

if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

if exist "%PYTHON_DIR%\python.exe" (
    echo [+] Python bereits vorhanden. Springe zum Setup...
    goto PIP_CHECK
)

echo [+] Lade Python Embeddable Package herunter...
bitsadmin /transfer "PythonDownload" "%PYTHON_ZIP_URL%" "%NATIVE_DIR%\python.zip"

echo [+] Entpacke Python...
powershell -command "Expand-Archive -Path '%NATIVE_DIR%\python.zip' -DestinationPath '%PYTHON_DIR%' -Force"
del "%NATIVE_DIR%\python.zip"

echo [+] Konfiguriere Python-Pfad...
REM Aktiviere site-packages im embeddable Python
for %%i in ("%PYTHON_DIR%\python3*.zip") do set "ZIP_NAME=%%~nxi"
for %%f in ("%PYTHON_DIR%\python3*._pth") do (
    echo !ZIP_NAME!> "%%f"
    echo .>> "%%f"
    echo import site>> "%%f"
)

:PIP_CHECK
if exist "%PYTHON_DIR%\Scripts\pip.exe" (
    echo [+] Pip bereits vorhanden.
    goto INSTALL_REQS
)

echo [+] Lade get-pip.py herunter...
bitsadmin /transfer "PipDownload" "%GET_PIP_URL%" "%PYTHON_DIR%\get-pip.py"

echo [+] Installiere pip...
"%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
del "%PYTHON_DIR%\get-pip.py"

:INSTALL_REQS
echo [+] Bereite Installation vor...

REM Wir erstellen eine temporaere requirements-Datei, um den Tippfehler 'Django==6.0.2' 
REM lokal auf 'Django==5.0.2' zu korrigieren, falls er existiert.
REM Das laesst das Haupt-File fuer Docker unangetastet.
set "TEMP_REQS=%NATIVE_DIR%\temp_requirements.txt"
powershell -command "(Get-Content '%PROJECT_ROOT%\requirements.txt') -replace 'Django==6.0.2', 'Django==5.0.2' | Set-Content '%TEMP_REQS%'"

echo [+] Installiere Abhaengigkeiten (dies kann einen Moment dauern)...
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location -r "%TEMP_REQS%"

REM Aufraeumen
if exist "%TEMP_REQS%" del "%TEMP_REQS%"

echo.
echo ==========================================
echo   SETUP ABGESCHLOSSEN!
echo ==========================================
echo Du kannst das Dashboard nun mit 
echo 'start-dashboard.bat' starten.
pause
