# Builds dist\Quasar\Quasar.exe (icon embedded). Usage: .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "C:\Users\Inv11\AppData\Local\Programs\Python\Python312\python.exe" }
& $py -m pip install -r requirements.txt
& $py tools\make_icon.py
& $py -m pytest -q
& $py -m PyInstaller --noconfirm --clean --windowed --name Quasar `
    --icon assets\quasar.ico --add-data "assets;assets" `
    --collect-submodules keyring.backends `
    run_quasar.py
Write-Host "Built: $PSScriptRoot\dist\Quasar\Quasar.exe"
