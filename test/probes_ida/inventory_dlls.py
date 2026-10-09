import struct, os, winreg, subprocess
SYS32 = os.path.join(os.environ['SystemRoot'], 'System32')
ROOT = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'

def pe_exp_imp(path):
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
    # exports
    erva = struct.unpack_from('<I', d, ddoff)[0]
    exp = []
    expname = ''
    if erva:
        o = r2o(erva)
        if o:
            nr = struct.unpack_from('<I', d, o + 0x0C)[0]
            nnames = struct.unpack_from('<I', d, o + 0x18)[0]
            npo = r2o(struct.unpack_from('<I', d, o + 0x20)[0])
            no = r2o(nr)
            if no: expname = d[no:no+80].split(b'\x00')[0].decode('latin1')
            if npo:
                for i in range(nnames):
                    x = struct.unpack_from('<I', d, npo + i*4)[0]
                    xo = r2o(x)
                    if xo: exp.append(d[xo:xo+128].split(b'\x00')[0].decode('latin1'))
    # imports
    irva = struct.unpack_from('<I', d, ddoff + 8)[0]
    imps = []
    if irva:
        o = r2o(irva)
        if o:
            i = 0
            while i < 400:
                ent = d[o+i*20: o+i*20+20]
                if len(ent) < 20 or ent == b'\x00'*20: break
                nr = struct.unpack_from('<I', ent, 12)[0]
                if not nr: break
                no2 = r2o(nr)
                if no2 is None: break
                imps.append(d[no2:no2+80].split(b'\x00')[0].decode('latin1'))
                i += 1
    return exp, expname, imps, d

# KnownDLLs
k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
    r'SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs')
known = set()
for i in range(winreg.QueryInfoKey(k)[1]):
    known.add(winreg.EnumValue(k, i)[0].lower())

# hoi4.exe 的导入
hexp, hexpn, himp, hd = pe_exp_imp(os.path.join(ROOT, 'hoi4.exe'))
himp_set = set(x.lower() for x in himp)
print('hoi4.exe 导入 %d 个模块' % len(himp))
print()
print('%-24s %8s %6s %6s %6s  %s' % ('DLL','KB','导出','导入它','Known','说明'))
print('-'*92)
for f in sorted(os.listdir(ROOT)):
    if not f.lower().endswith('.dll'): continue
    fp = os.path.join(ROOT, f)
    try:
        exp, expn, imps, d = pe_exp_imp(fp)
    except Exception as e:
        print('%-24s  (解析失败 %s)' % (f, e)); continue
    kb = os.path.getsize(fp)/1024
    bare = f.lower().replace('.dll','')
    inknown = 'YES' if bare in known else 'no'
    # 谁导入它
    importers = []
    if f.lower() in himp_set: importers.append('hoi4')
    for g in os.listdir(ROOT):
        if not g.lower().endswith('.dll') or g == f: continue
        try:
            _, _, gimp, _ = pe_exp_imp(os.path.join(ROOT, g))
        except Exception:
            continue
        if f.lower() in set(x.lower() for x in gimp):
            importers.append(g.replace('.dll',''))
    note = ''
    if f.lower() in ('dxgi.dll','dxgi_real.dll'): note = '本项目放置的'
    elif f.lower() in ('juij_steam.dll','version.dll','winmm.dll','winhttp.dll'): note = '第三方整合包'
    elif f.lower() == 'steam_api64_o.dll': note = '原版备份(有人已替换过)'
    print('%-24s %8.1f %6d %6d %6s  %s' % (f, kb, len(exp), len(importers), inknown, note))
    if importers: print('%-24s         导入者: %s' % ('', ', '.join(importers)))
