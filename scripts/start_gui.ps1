$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$Python = "pythonw"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$VenvPythonFallback = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
} elseif (Test-Path -LiteralPath $VenvPythonFallback) {
    $Python = $VenvPythonFallback
}

Start-Process -NoNewWindow -FilePath $Python -ArgumentList "-m autosite gui"
