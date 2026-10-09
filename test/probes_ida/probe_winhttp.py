import struct, sys, os
SYS32 = os.path.join(os.environ['SystemRoot'], 'System32')
ROOT = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'

def pe_info(path):
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
        nm = b[:8].rstrip(b'\x00').decode('latin1')
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
        secs.append((nm, vaddr, vsize, raw, rsize))
    def r2o(rva):
        for nm, vaddr, vsize, raw, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raw + (rva - vaddr)
        return None
    def dirnames(idx, isexp):
        rva, size = struct.unpack_from('<II', d, ddoff + idx*8)
        if not rva: return []
        o = r2o(rva)
        if o is None: return []
        if isexp:
            nr = struct.unpack_from('<I', d, o + 0x0C)[0]
            no = r2o(nr)
            return [d[no:no+80].split(b'\x00')[0].decode('latin1')] if no else []
        res = []
        i = 0
        while i < 300:
            ent = d[o+i*20: o+i*20+20]
            if len(ent) < 20 or ent == b'\x00'*20: break
            nr = struct.unpack_from('<I', ent, 12)[0]
            if not nr: break
            no = r2o(nr)
            if no is None: break
            res.append(d[no:no+80].split(b'\x00')[0].decode('latin1'))
            i += 1
        return res
    return dirnames(0, True), dirnames(1, False), secs, d

print('=== 游戏目录 winhttp.dll 详情 ===')
fp = os.path.join(ROOT, 'winhttp.dll')
exp, imp, secs, d = pe_info(fp)
print('大小 = %.1f KB' % (os.path.getsize(fp)/1024))
print('导出模块名 = %s' % (exp[0] if exp else '-'))
print('节 = %s' % ', '.join(s[0] for s in secs))
print('导入 (%d): %s' % (len(imp), ', '.join(imp)))
print('')
# 找内部可疑字符串：doorstop / bepinex / mono
kws = [b'doorstop', b'Doorstop', b'BepInEx', b'bepinex', b'winhttp', b'config.ini',
       b'doorstop_config', b'Managed', b'Mono', b'mono-2.0', b'UnityPlayer']
print('=== 内嵌关键字扫描 ===')
for k in kws:
    c = d.count(k)
    if c:
        print('  %-20s 出现 %d 次' % (k.decode('latin1'), c))
print('')
print('=== 对比：系统 winhttp.dll ===')
fp2 = os.path.join(SYS32, 'winhttp.dll')
exp2, imp2, secs2, d2 = pe_info(fp2)
print('大小 = %.1f KB' % (os.path.getsize(fp2)/1024))
print('导出模块名 = %s' % (exp2[0] if exp2 else '-'))
print('导入 (%d): %s' % (len(imp2), ', '.join(imp2)))
print('')
print('=== 游戏目录 winhttp.dll 与系统版是否同一文件 ===')
print('字节数 游戏=%d 系统=%d  相同=%s' % (len(d), len(d2), len(d) == len(d2)))
print('')
print('=== Juij_Steam.dll vs version.dll 是否同一文件 ===')
a = open(os.path.join(ROOT, 'Juij_Steam.dll'), 'rb').read()
b = open(os.path.join(ROOT, 'version.dll'), 'rb').read()
c = open(os.path.join(ROOT, 'winmm.dll'), 'rb').read()
print('Juij_Steam == version : %s (%d vs %d)' % (a == b, len(a), len(b)))
print('Juij_Steam == winmm   : %s' % (a == c))
