# Builds dist\Quasar\Quasar.exe. Dependencies must already be installed.
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "C:\Users\Inv11\AppData\Local\Programs\Python\Python312\python.exe" }
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QPA_FONTDIR = "C:\Windows\Fonts"
if (-not $env:PYINSTALLER_CONFIG_DIR) {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot ".pyinstaller-cache"
}
if (-not $SkipTests) {
    & $py -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed (exit $LASTEXITCODE)." }
}
& $py -m PyInstaller --noconfirm --clean --windowed --name Quasar `
    --icon assets\quasar.ico --add-data "assets;assets" `
    --collect-submodules keyring.backends `
    run_quasar.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)." }
if (-not (Test-Path dist\Quasar\Quasar.exe)) { throw "Build did not produce Quasar.exe." }
Write-Host "Built: $PSScriptRoot\dist\Quasar\Quasar.exe"
