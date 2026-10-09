import struct
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
d = open(p,'rb').read()
e = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, e+6)[0]
optsz = struct.unpack_from('<H', d, e+20)[0]
sec = e + 24 + optsz
secs = []
for i in range(nsec):
    off = sec + i*40
    nm = d[off:off+8].split(b'\x00')[0].decode('latin1')
    vsz, va, rsz, ra = struct.unpack_from('<IIII', d, off+8)
    secs.append((nm, va, vsz, ra, rsz))
def f2r(fo):
    for nm, va, vsz, ra, rsz in secs:
        if ra <= fo < ra + rsz: return va + (fo - ra)
def r2f(rva):
    for nm, va, vsz, ra, rsz in secs:
        if va <= rva < va + max(vsz, rsz): return ra + (rva - va)
# 找 resistance.cpp 附近的全部日志字符串
base_fo = d.find(b'C:\\mnt\\gsg\\hoi4\\hoi4_merged\\hoi4\\source\\resistance.cpp')
print('resistance.cpp 字符串 fileoff=%#x  RVA=%#x' % (base_fo, f2r(base_fo)))
seg = d[base_fo:base_fo+1400]
print('=== 该文件用到的全部日志字符串 ===')
import re
for m in re.finditer(rb'[\x20-\x7e]{12,}', seg):
    s = m.group().decode()
    if len(s) >= 12:
        fo = base_fo + m.start()
        print('  rva=%#x  %r' % (f2r(fo), s[:95]))
