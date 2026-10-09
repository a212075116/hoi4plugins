$ErrorActionPreference='Stop'
$here = 'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\flirt\loader'
$build = Join-Path $here 'build'
$vc = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
$bat = Join-Path $build 'b_early.bat'
@(
    '@echo off',
    "call `"$vc`" >nul 2>&1",
    "cd /d `"$build`"",
    "cl /nologo /LD /O2 /W3 /utf-8 /EHsc /std:c++17 /DCARRIER_EARLY_THREAD /I`"$here`" `"$here\carrier_loader.cpp`" /link /out:tbb_early.dll /machine:x64 carrier_exp.exp shell32.lib ole32.lib user32.lib",
    'echo EARLY_EXIT=%errorlevel%'
) | Set-Content $bat -Encoding ASCII
cmd /c $bat 2>&1 | Select-Object -Last 5
Get-ChildItem (Join-Path $build 'tbb_early.dll') -ErrorAction SilentlyContinue | Select-Object Name, Length | Format-Table -AutoSize | Out-String