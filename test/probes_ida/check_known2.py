import winreg, os, struct

# --- 1. KnownDLLs 正确查询（键名不带 .dll） ---
k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
    r'SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs')
n = winreg.QueryInfoKey(k)[1]
entries = {}
for i in range(n):
    name, val, _ = winreg.EnumValue(k, i)
    entries[name.lower()] = val
known_bare = set(entries.keys())

def in_known(dll):
    return dll.lower().replace('.dll','') in known_bare

cands = ['dxgi.dll','d3d9.dll','d3d11.dll','version.dll','winmm.dll','winhttp.dll',
         'XInput1_3.dll','xinput1_4.dll','d3dx9_43.dll','openGL32.dll',
         'd3dcompiler_47.dll','tbb.dll','imm32.dll','shlwapi.dll','setupapi.dll',
         'psapi.dll','combase.dll','ws2_32.dll','dbghelp.dll','hid.dll','avrt.dll',
         'comctl32.dll','userenv.dll','cfgmgr32.dll','bcrypt.dll','crypt32.dll']
print('=== KnownDLLs 判定（修正版：键名不带 .dll）===')
print()
print('【不可劫持 — 在 KnownDLLs 内】')
for c in cands:
    if in_known(c): print('   %-22s -> %s' % (c, entries[c.lower().replace('.dll','')]))
print()
print('【可劫持 — 不在 KnownDLLs 内】')
for c in cands:
    if not in_known(c): print('   %s' % c)
print()

# --- 2. 谁导入了 winhttp.dll ---
ROOT = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
def imports_of(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    nsec = struct.unpack_from('<H', d, pe+6)[0]
    optsz = struct.unpack_from('<H', d, pe+20)[0]
    magic = struct.unpack_from('<H', d, pe+24)[0]
    ddoff = pe + 24 + (112 if magic == 0x20B else 96)
    secs = []
    off = pe + 24 + optsz
    for i in range(nsec):
        b = d[off+i*40: off+i*40+40]
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
        secs.append((vaddr, vsize, raw, rsize))
    def r2o(rva):
        for vaddr, vsize, raw, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raw + (rva - vaddr)
        return None
    rva, size = struct.unpack_from('<II', d, ddoff + 8)
    if not rva: return []
    o = r2o(rva)
    if o is None: return []
    res = []; i = 0
    while i < 400:
        ent = d[o+i*20: o+i*20+20]
        if len(ent) < 20 or ent == b'\x00'*20: break
        nr = struct.unpack_from('<I', ent, 12)[0]
        if not nr: break
        no = r2o(nr)
        if no is None: break
        res.append(d[no:no+80].split(b'\x00')[0].decode('latin1'))
        i += 1
    return res

print('=== 游戏目录各 DLL 是否导入 winhttp.dll ===')
for f in sorted(os.listdir(ROOT)):
    if not f.lower().endswith('.dll'): continue
    fp = os.path.join(ROOT, f)
    try:
        imps = imports_of(fp)
    except Exception as e:
        print('   %-28s (解析失败)' % f); continue
    hits = [x for x in imps if 'winhttp' in x.lower()]
    if hits:
        print('   %-28s >>> %s' % (f, ', '.join(hits)))
print()
print('=== hoi4.exe 是否导入 winhttp ===')
ex = imports_of(os.path.join(ROOT, 'hoi4.exe'))
print('   hoi4.exe 导入 %d 个模块, winhttp = %s' % (
    len(ex), [x for x in ex if 'winhttp' in x.lower()] or '无'))
