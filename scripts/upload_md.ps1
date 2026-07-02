param([string]$FilePath)

$ProjectRoot = Split-Path -Parent $PSScriptRoot

$result = & python -m autosite upload "$FilePath" 2>&1
$exitCode = $LASTEXITCODE

Write-Host $result

if ($exitCode -ne 0) {
    $null = [System.Windows.Forms.MessageBox]::Show("上传失败`n`n文件：$FilePath`n请查看命令行输出了解详情。", "上传失败", "OK", "Error")
}

exit $exitCode
