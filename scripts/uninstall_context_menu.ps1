$commandKey = "HKCU:\Software\Classes\SystemFileAssociations\.md\shell\UploadToThrecial"

if (Test-Path $commandKey) {
    try {
        Remove-Item -Path $commandKey -Recurse -Force
        Write-Host "[OK] Context menu uninstalled"
    } catch {
        Write-Host "[ERROR] Failed to uninstall context menu: $_"
        exit 1
    }
} else {
    Write-Host "[INFO] Context menu not found, nothing to uninstall"
}
