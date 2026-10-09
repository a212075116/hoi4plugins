import winreg, os, struct
k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
    r'SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs')
n = winreg.QueryInfoKey(k)[1]
entries = {}
for i in range(n):
    name, val, _ = winreg.EnumValue(k, i)
    entries[name.lower()] = val
print('KnownDLLs 条目数 =', n)
print('')
cands = ['dxgi.dll','d3d9.dll','d3d11.dll','version.dll','winmm.dll','winhttp.dll',
         'XInput1_3.dll','XInput9_1_0.dll','xinput1_4.dll','d3dx9_43.dll','openGL32.dll',
         'd3dcompiler_47.dll','tbb.dll','imm32.dll','shlwapi.dll','setupapi.dll','ws2_32.dll',
         'psapi.dll','dbghelp.dll','hid.dll','avrt.dll','comctl32.dll','userenv.dll',
         'cfgmgr32.dll','combase.dll','bcrypt.dll','crypt32.dll','pdbsdk.dll']
print('%-22s %-12s %s' % ('查询名', '在KnownDLLs', '含义'))
print('-' * 62)
for c in cands:
    hit = entries.get(c.lower())
    mark = 'YES' if hit else 'no'
    note = ('-> ' + hit) if hit else '可选择劫持目标'
    print('%-22s %-12s %s' % (c, mark, note))
print('')
print('=== 全部 KnownDLLs 条目 ===')
for name in sorted(entries):
    print('  %-24s -> %s' % (name, entries[name]))
