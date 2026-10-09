# build_carrier.ps1 -- 用「游戏自带 DLL」做载体的引导器构建脚本
#
# 设计要点:
#   1. 载体是游戏根目录原本就有的 DLL, 不新增文件, 玩家看不出异常。
#      代价: 该文件在 Steam depot manifest 内, 玩家执行「验证游戏文件完整性」
#      会被还原成原版, 引导器随之失效（新增文件如 dxgi.dll 则不会被还原）。
#   2. tbb.dll 被选为默认载体: 游戏自带 + 未被第三方替换 + 不在 KnownDLLs
#      + hoi4.exe 只从它导入 22 个函数。
#   3. 解析源永远是 _real 备份(原版), 避免「解析到自己的引导器」造成自我覆盖。
#   4. 部署前用 check_exports.py 校验导出集合完整, 不一致就拒绝部署。
param(
    [string]$Carrier = 'tbb.dll',
    [string]$GameDir = 'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
)
$ErrorActionPreference = 'Stop'
$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$build = Join-Path $here 'build'
New-Item -ItemType Directory -Force -Path $build | Out-Null
New-Item -ItemType Directory -Force -Path ($GameDir + '\reports') | Out-Null

$base        = $Carrier -replace '\.dll$',''
$realName    = $base + '_real.dll'
$carrierPath = Join-Path $GameDir $Carrier
$realPath    = Join-Path $GameDir $realName
$logDirFwd   = ($GameDir -replace '\\','/') + '/reports'
$py    = 'C:/Users/a2120/AppData/Local/Programs/Python/Python313/python.exe'
$vcvars = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'

Write-Host ("carrier = {0}   real = {1}" -f $Carrier, $realName) -ForegroundColor Cyan

Write-Host '=== 0. 定位原版 ===' -ForegroundColor Cyan
if (-not (Test-Path $realPath)) {
    Copy-Item $carrierPath $realPath -Force
    Write-Host ("  首次运行: 已备份原版 -> {0}" -f $realName)
}
$curLen = (Get-Item $carrierPath).Length
$refLen = (Get-Item $realPath).Length
if ($curLen -ne $refLen) {
    Copy-Item $realPath $carrierPath -Force
    Write-Host '  载体曾被替换, 已用备份还原'
}
$srcDll = $realPath
Write-Host ("  原版 = {0}  ({1} bytes)" -f $realName, $refLen)

# 注意: @() 里多行用 + 拼接会被 PowerShell 当成单个表达式, 故用显式拼接
$hdr  = '#define LOADER_LOG_DIR "' + $logDirFwd + '"' + "`r`n"
$hdr += '#define CARRIER_LIBRARY "' + $base + '"' + "`r`n"
$hdr += '#define CARRIER_REAL "' + $base + '_real"' + "`r`n"
[System.IO.File]::WriteAllText((Join-Path $here 'carrier.h'), $hdr, [System.Text.Encoding]::ASCII)

Write-Host '=== 1. 生成转发 .def ===' -ForegroundColor Cyan
& $py (Join-Path $here 'gen_def.py') $srcDll (Join-Path $build 'carrier.def') $base ($base + '_real')

Write-Host '=== 2. 编译引导器 ===' -ForegroundColor Cyan
$bat = Join-Path $build 'b_carrier.bat'
@(
    '@echo off',
    "call `"$vcvars`" >nul 2>&1",
    "cd /d `"$build`"",
    'lib /nologo /def:carrier.def /out:carrier_exp.lib /machine:x64 >nul',
    "cl /nologo /LD /O2 /W3 /utf-8 /EHsc /std:c++17 /I`"$here`" `"$here\carrier_loader.cpp`" /link /out:$Carrier /machine:x64 carrier_exp.exp shell32.lib ole32.lib user32.lib",
    'echo EXIT=%errorlevel%'
) | Set-Content $bat -Encoding ASCII
$o = cmd /c $bat 2>&1
$built = Join-Path $build $Carrier
if (-not (Test-Path $built)) {
    Write-Host '  编译失败' -ForegroundColor Red
    $o | Select-Object -Last 8 | ForEach-Object { Write-Host ('    ' + $_) }
    exit 1
}
Write-Host '  编译成功' -ForegroundColor Green

Write-Host '=== 3. 校验导出集合 ===' -ForegroundColor Cyan
& $py (Join-Path $here 'check_exports.py') $built $srcDll
if ($LASTEXITCODE -ne 0) {
    Write-Host '  !! 导出不完整, 拒绝部署(否则游戏会启动失败)' -ForegroundColor Red
    exit 1
}

Write-Host '=== 4. 部署 ===' -ForegroundColor Cyan
Copy-Item $built $carrierPath -Force
Write-Host ("  载体已替换: {0}" -f $Carrier)
Write-Host ("  原版备份:   {0}" -f $realName) -ForegroundColor DarkGray

# 插件与载体同放游戏根目录, 命名为引导器约定的 hoi4_mod_plugin.dll。
# 不再碰 mod 目录: mod 目录不在 DLL 搜索路径里, 只能靠我们主动去扫,
# 那会把整套方案绑死在 mod 的布局上。
# 增量判断必须比较源文件时间戳, 不能只判断文件是否存在 ——
# 否则改了 mod_plugin.c 之后会一直复用旧产物（这个坑踩过一次:
# 日志里出现的是改动前的旧行为, 会让人误判代码没生效）。
$plugin = Join-Path $build 'mod_plugin.dll'
$pluginSrc = Join-Path $here 'mod_plugin.c'
$needBuild = $true
if ((Test-Path $plugin) -and (Test-Path $pluginSrc)) {
    if ((Get-Item $plugin).LastWriteTime -ge (Get-Item $pluginSrc).LastWriteTime) {
        $needBuild = $false
        Write-Host '  插件源文件未变, 跳过重编' -ForegroundColor DarkGray
    }
}
if ($needBuild) {
    $pb = Join-Path $build 'b_plugin.bat'
    @(
        '@echo off',
        "call `"$vcvars`" >nul 2>&1",
        "cd /d `"$build`"",
        "cl /nologo /LD /O2 /W3 /utf-8 /I`"$here`" `"$here\mod_plugin.c`" /link /out:mod_plugin.dll /machine:x64 user32.lib",
        'echo EXIT=%errorlevel%'
    ) | Set-Content $pb -Encoding ASCII
    cmd /c $pb | Out-Null
}
if (Test-Path $plugin) {
    $dest = Join-Path $GameDir 'hoi4_mod_plugin.dll'
    Copy-Item $plugin $dest -Force
    Write-Host ("  插件已部署: {0}  ({1} bytes)" -f $dest, (Get-Item $dest).Length)
}
Write-Host ''
Write-Host 'next: .\run_test.ps1' -ForegroundColor Cyan