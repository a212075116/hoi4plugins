Set-Location 'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
Get-Process hoi4,CrashReporter -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Remove-Item 'crashes' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path 'crashes' | Out-Null
'=== 启动 WMI 进程监控 (后台) ==='
$job = Start-Job -ScriptBlock {
  Get-WmiObject -Class Win32_ProcessStartTrace -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like '*rash*' -or $_.ProcessName -like 'hoi4*' } |
    ForEach-Object { $_.ProcessName + '  pid=' + $_.ProcessID + '  parent=' + $_.ParentProcessID }
}
Start-Process -FilePath 'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe' -ArgumentList '-gdpr-compliant -start_tag=CHI -nolauncher' -WorkingDirectory 'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
Start-Sleep -Seconds 40
$env:PYTHONIOENCODING='utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
& 'C:/Users/a2120/AppData/Local/Programs/Python/Python313/python.exe' -u 'hoi4plugins/test/tools/_proc3.py' 2>&1 | Select-Object -Last 3
Start-Sleep -Seconds 15
'=== WMI 监控结果 ==='
Receive-Job $job -Keep
Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue
'=== 当前进程 ==='
Get-Process hoi4,CrashReporter -ErrorAction SilentlyContinue | ForEach-Object { '  ' + $_.ProcessName + '  pid=' + $_.Id }
'=== 根目录 crashes ==='
Get-ChildItem 'crashes' -Recurse -File | ForEach-Object { '  ' + $_.Name + '  ' + $_.Length }
$d = Join-Path $env:USERPROFILE 'Documents\Paradox Interactive\Hearts of Iron IV\crashes'
'Documents 数量: ' + (Get-ChildItem $d -Directory).Count
