# -*- coding: utf-8 -*-
# 只读：检查 hoi4.exe 是否使用 SteamStub DRM
import struct, sys, os
W = r'D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV'
p = os.path.join(W, 'hoi4.exe')
data = open(p, 'rb').read()
print('file size = %d' % len(data))
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
assert data[e_lfanew:e_lfanew+4] == b'PE\x00\x00', 'not PE'
coff = e_lfanew + 4
machine, nsec, _, _, _, optsz, chars = struct.unpack_from('<HHIIIHH', data, coff)
print('machine = 0x%X  sections = %d  opt hdr = %d  characteristics = 0x%X' % (machine, nsec, optsz, chars))
opt = coff + 20
magic = struct.unpack_from('<H', data, opt)[0]
print('opt magic = 0x%X (%s)' % (magic, 'PE32+' if magic == 0x20B else 'PE32'))
ep = struct.unpack_from('<I', data, opt + 16)[0]
imgbase = struct.unpack_from('<Q', data, opt + 24)[0] if magic == 0x20B else struct.unpack_from('<I', data, opt + 28)[0]
print('entrypoint RVA = 0x%X  imagebase = 0x%X' % (ep, imgbase))
secoff = opt + optsz
names = []
for i in range(nsec):
    off = secoff + i * 40
    nm = data[off:off+8].rstrip(b'\x00').decode('ascii', 'replace')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off + 8)
    ch = struct.unpack_from('<I', data, off + 36)[0]
    names.append(nm)
    print('  %-10s VA=0x%-8X vsize=0x%-8X raw=0x%-8X ptr=0x%-8X ch=0x%X' % (nm, vaddr, vsize, rawsize, rawptr, ch))
sus = [n for n in names if n.lower() in ('.bind', '.vmp0', '.themida', 'upx0', 'upx1', '.enigma')]
print('suspicious sections: %s' % (sus if sus else 'NONE'))
print('has .bind: %s' % ('.bind' in names))
for kw in (b'SteamStub', b'Steamless', b'steamstub', b'SteamDRM', b'SteamAPI_Init', b'steam_api64.dll'):
    c = data.count(kw)
    print('  %-20s count=%d' % (kw.decode(), c))
# 入口点所在段
for i in range(nsec):
    off = secoff + i * 40
    nm = data[off:off+8].rstrip(b'\x00').decode('ascii', 'replace')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off + 8)
    if vaddr <= ep < vaddr + max(vsize, rawsize):
        print('entrypoint is in section: %s (offset in section 0x%X)' % (nm, ep - vaddr))
# 导入表里的 dll
print('imports (dll names found):')
import re
for m in sorted(set(re.findall(rb'[A-Za-z0-9_\-\.]+\.dll', data[:0x200000]))):
    print('   ', m.decode('ascii', 'replace'))