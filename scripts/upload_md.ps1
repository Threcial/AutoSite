param([string]$FilePath)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$Python = "python"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
}

$result = & $Python -m autosite upload "$FilePath" 2>&1
$exitCode = $LASTEXITCODE

Write-Host $result

if ($exitCode -ne 0) {
    try {
        Add-Type -AssemblyName System.Windows.Forms | Out-Null
        $null = [System.Windows.Forms.MessageBox]::Show("上传失败`n`n文件：$FilePath`n请查看命令行输出了解详情。", "上传失败", "OK", "Error")
    } catch {
        Write-Host "[WARN] Failed to show popup: $_"
    }
}

exit $exitCode
