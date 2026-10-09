import struct
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
d = open(p,'rb').read()
e_lfanew = struct.unpack_from('<I', d, 0x3c)[0]
print('PE sig = %r' % d[e_lfanew:e_lfanew+4])
nsec = struct.unpack_from('<H', d, e_lfanew+6)[0]
optsz = struct.unpack_from('<H', d, e_lfanew+20)[0]
opt = e_lfanew + 24
magic = struct.unpack_from('<H', d, opt)[0]
print('magic=%#x  sections=%d' % (magic, nsec))
# data directories: PE32+ 从 opt+112 开始
dd = opt + 112
imp_rva, imp_sz = struct.unpack_from('<II', d, dd + 1*8)
print('import dir rva=%#x size=%#x' % (imp_rva, imp_sz))
# 段表
sec = e_lfanew + 20 + optsz
secs = []
for i in range(nsec):
    off = sec + i*40
    nm = d[off:off+8].rstrip(b'\x00').decode('latin1')
    vsz, va, rsz, ra = struct.unpack_from('<IIII', d, off+8)
    secs.append((nm, va, vsz, ra, rsz))
    print('  sec %-8s va=%#010x vsz=%#x ra=%#x rsz=%#x' % (nm, va, vsz, ra, rsz))
def r2o(rva):
    for nm, va, vsz, ra, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return ra + (rva - va)
    return None
o = r2o(imp_rva)
import re
names = []
i = 0
while True:
    ent = o + i*20
    oft, ts, fwd, namerva, fta = struct.unpack_from('<IIIII', d, ent)
    if namerva == 0: break
    no = r2o(namerva)
    end = d.index(b'\x00', no)
    dll = d[no:end].decode('latin1')
    names.append(dll)
    i += 1
print()
print('导入的 DLL 数: %d' % len(names))
for n in names: print('  ' + n)
key = [n for n in names if 'kernel32' in n.lower() or 'kernelbase' in n.lower()]
print()
print('kernel32/kernelbase: %s' % key)
