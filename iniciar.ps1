$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -3 start.py
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source start.py
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "ERROR: No se encontro Python 3.10+ en el PATH." -ForegroundColor Red
Write-Host "Instala Python desde https://www.python.org/downloads/"
exit 1
