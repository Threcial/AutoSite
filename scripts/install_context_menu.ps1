$menuName = "上传到 threcial.cn"
$commandKey = "HKCU:\Software\Classes\SystemFileAssociations\.md\shell\UploadToThrecial"
$commandValue = "`"$PSScriptRoot\upload_md.ps1`" `"%1`""

try {
    New-Item -Path $commandKey -Force | Out-Null
    Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $menuName
    New-Item -Path "$commandKey\command" -Force | Out-Null
    Set-ItemProperty -Path "$commandKey\command" -Name "(Default)" -Value "powershell -NoProfile -ExecutionPolicy Bypass -File $commandValue"
    Write-Host "[OK] Context menu installed: $menuName"
    Write-Host "     Registry: $commandKey"
} catch {
    Write-Host "[ERROR] Failed to install context menu: $_"
    exit 1
}
