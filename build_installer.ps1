# build_installer.ps1
param(
    [switch]$InstallerOnly,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$distPath = Join-Path $ProjectRoot "dist\FinanzplanDesktop"

# 1. Pre-Check: Prüfen ob dist\FinanzplanDesktop blockiert ist
if (-not $InstallerOnly -and (Test-Path $distPath)) {
    while ($true) {
        $locked = $false
        try {
            $testName = "FinanzplanDesktop_locktest"
            Rename-Item -Path $distPath -NewName $testName -ErrorAction Stop
            Rename-Item -Path (Join-Path $ProjectRoot "dist\$testName") -NewName "FinanzplanDesktop" -ErrorAction Stop
        } catch {
            $locked = $true
        }

        if (-not $locked) {
            break
        }

        Write-Host "`n[WARNUNG] Der Ordner '$distPath' ist durch einen anderen Prozess gesperrt!" -ForegroundColor Yellow
        Write-Host "Bitte alle Explorer-Fenster und Terminals schließen, die in diesem Ordner geöffnet sind." -ForegroundColor Yellow
        Write-Host "Drücke [Enter] zum erneuten Versuch oder 'q' zum Abbrechen: " -ForegroundColor Cyan -NoNewline
        $resp = [Console]::ReadLine()
        if ($resp -match "^[qQ]") {
            exit 1
        }
    }
}

if (-not $InstallerOnly) {
    Write-Host "=== 1/3: Collecting static files ===" -ForegroundColor Cyan
    python manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "`n=== 2/3: Running PyInstaller ===" -ForegroundColor Cyan
    $pyiArgs = @("-y", "finanzplan.spec")
    if ($Clean) {
        $pyiArgs = @("--clean") + $pyiArgs
    }
    python -m PyInstaller @pyiArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Überspringe PyInstaller (-InstallerOnly aktiv) ===" -ForegroundColor Yellow
}

Write-Host "`n=== 3/3: Building Inno Setup Installer ===" -ForegroundColor Cyan
$isccPaths = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Error "ISCC.exe (Inno Setup 6) nicht gefunden!"
    exit 1
}

& $iscc installer.iss
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[SUCCESS] Installer erstellt: dist_installer\FinanzplanDesktop_Setup.exe" -ForegroundColor Green
