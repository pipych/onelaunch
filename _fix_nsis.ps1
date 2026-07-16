$src = "C:\Users\pshen\.openclaw\workspace\onelaunch\installer\OneLaunch.nsi"
$txt = [System.IO.File]::ReadAllText($src, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($src, $txt, [System.Text.Encoding]::GetEncoding(1251))
Write-Host "Fixed encoding to CP1251"

# Verify
$check = [System.IO.File]::ReadAllText($src, [System.Text.Encoding]::GetEncoding(1251))
if ($check -match "Создать") { Write-Host "Russian text OK" } else { Write-Host "Still broken" }

# Rebuild NSIS
$makensis = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
& $makensis "C:\Users\pshen\.openclaw\workspace\onelaunch\installer\OneLaunch.nsi"
Write-Host "NSIS exit: $LASTEXITCODE"

# Check files
Get-ChildItem "C:\Users\pshen\.openclaw\workspace\onelaunch\installer\*.exe" | Select Name,Length
Get-ChildItem "C:\Users\pshen\.openclaw\workspace\onelaunch\dist\*.zip" | Select Name,Length
