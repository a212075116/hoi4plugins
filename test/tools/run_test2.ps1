# run_test2.ps1 -- 信号驱动的端到端测试
#
# 不靠固定睡眠：游戏走到哪一步，由引导器/插件写进日志的事实决定。
# 这里只轮询「最终答案有没有出现」，出现就立刻收工，避免白等。
# 仍然保留一个上限，但它是保险丝，不是计时器。
param(
    [string]$GameDir = 'D:\SteamLibrary\steamapps\common\Hearts of Iron IV',
    [string]$Carrier = 'tbb.dll',
    [int]$MaxWaitSec = 240
)
$ErrorActionPreference = 'Stop'
$base = $Carrier -replace '\.dll$',''
$log  = Join-Path $GameDir ('reports/mod_loader_' + $base + '.log')

if (Get-Process 'hoi4' -ErrorAction SilentlyContinue) {
    Write-Host '[!] 游戏正在运行, 先关掉' -ForegroundColor Yellow
    exit 1
}
Remove-Item $log -Force -ErrorAction SilentlyContinue

Write-Host "[*] 启动 $GameDir\hoi4.exe"
$proc = Start-Process -FilePath (Join-Path $GameDir 'hoi4.exe') -WorkingDirectory $GameDir -PassThru

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$hit = $null
while ($sw.Elapsed.TotalSeconds -lt $MaxWaitSec) {
    if ($proc.HasExited) { $hit = '游戏进程已退出 (exit=' + $proc.ExitCode + ')'; break }
    if (Test-Path $log) {
        $txt = Get-Content $log -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($txt) {
            if ($txt -match [regex]::Escape('结论:'))   { $hit = '结论:';          break }
            if ($txt -match [regex]::Escape('还是 NULL')) { $hit = '还是 NULL';     break }
            if ($txt -match [regex]::Escape('加载失败'))   { $hit = '加载失败';      break }
        }
    }
    Start-Sleep -Milliseconds 300
}
$sw.Stop()
Write-Host ('[*] 等到信号: {0}   用时 {1:N1} 秒' -f $hit, $sw.Elapsed.TotalSeconds)

$p = Get-Process 'hoi4' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) { Write-Host ('[*] 游戏存活: Responding={0}  WS={1} MB' -f $p.Responding, [int]($p.WorkingSet64/1MB)) }
else    { Write-Host '[!] 游戏已退出' -ForegroundColor Yellow }

Write-Host '--- 日志 ---' -ForegroundColor Cyan
if (Test-Path $log) { Get-Content $log -Encoding UTF8 } else { Write-Host '(无日志)' }