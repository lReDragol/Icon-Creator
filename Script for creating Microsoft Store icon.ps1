$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutName = "Microsoft Store.lnk"
$shortcutPath = Join-Path -Path $desktopPath -ChildPath $shortcutName
$appUserModelId = "Microsoft.WindowsStore_8wekyb3d8bbwe!App"
$wShell = New-Object -ComObject WScript.Shell
$shortcut = $wShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "explorer.exe"
$shortcut.Arguments = "shell:AppsFolder\$appUserModelId"
$shortcut.Description = "Открыть Microsoft Store"
$shortcut.IconLocation = "$env:SystemRoot\System32\winstore.dll"
$shortcut.Save()
