# run_test.ps1 -- 验证两个情况: 引导器被游戏加载 + mod 插件被引导器加载
#
# 用法:
#   .\run_test.ps1                      # 默认载体 tbb.dll
#   .\run_test.ps1 -Carrier PDXSDK.dll  # 换载体
param(
    [string]$Carrier = 'tbb.dll',
    [int]$WaitSeconds = 45,
    [string]$GameDir = 'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
)
$ErrorActionPreference = 'Continue'
$base = $Carrier -replace '\.dll$', ''
$log  = Join-Path $GameDir ('reports\mod_loader_' + $base + '.log')

Write-Host ('载体 = ' + $Carrier) -ForegroundColor Cyan
Write-Host ('日志 = ' + $log) -ForegroundColor DarkGray

Write-Host '=== 1. 清空全部旧日志 ===' -ForegroundColor Cyan
Get-ChildItem (Join-Path $GameDir 'reports') -Filter 'mod_loader_*.log' -ErrorAction SilentlyContinue | Remove-Item -Force
if (Test-Path $log) { throw ('无法清空 ' + $log) }
Write-Host '已清空'

Write-Host '=== 2. 关闭残留进程 ===' -ForegroundColor Cyan
Get-Process -Name 'hoi4' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

Write-Host '=== 3. 启动游戏 ===' -ForegroundColor Cyan
$p = Start-Process -FilePath (Join-Path $GameDir 'hoi4.exe') -WorkingDirectory $GameDir -PassThru
Write-Host ('pid = ' + $p.Id + '  等待 ' + $WaitSeconds + 's')
Start-Sleep -Seconds $WaitSeconds
$alive = Get-Process -Name 'hoi4' -ErrorAction SilentlyContinue
Write-Host ('游戏存活 = ' + [bool]$alive)
if ($alive) { Write-Host ('内存 = ' + [math]::Round($alive.WorkingSet64/1MB) + ' MB  响应 = ' + $alive.Responding) }

Write-Host '=== 4. 日志 ===' -ForegroundColor Cyan
if (-not (Test-Path $log)) {
    Write-Host '日志未生成 —— 引导器没被加载' -ForegroundColor Red
} else {
    Get-Content $log -Encoding UTF8 | ForEach-Object { Write-Host $_ }
    Write-Host ''
    $c = Get-Content $log -Encoding UTF8 -Raw
    Write-Host '=== 5. 判定 ===' -ForegroundColor Cyan
    if ($c -match '\[情况一\]') { Write-Host '  [OK] 情况一: 游戏根目录的载体被游戏加载' -ForegroundColor Green }
    else { Write-Host '  [NG] 情况一未成立' -ForegroundColor Red }
    if ($c -match '\[情况二\][^\r\n]*mod') { Write-Host '  [OK] 情况二: mod 目录的插件被引导器加载' -ForegroundColor Green }
    elseif ($c -match '情况二\] 未触发') { Write-Host '  [--] 情况二未触发: 没有 mod 插件' -ForegroundColor Yellow }
    else { Write-Host '  [NG] 情况二未成立' -ForegroundColor Red }
    if ($c -match '插件线程启动') { Write-Host '  [OK] mod 里的代码确实在游戏进程内执行了' -ForegroundColor Green }
    else { Write-Host '  [NG] mod 代码未执行' -ForegroundColor Red }
}

Write-Host '=== 6. 关闭游戏 ===' -ForegroundColor Cyan
Get-Process -Name 'hoi4' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2