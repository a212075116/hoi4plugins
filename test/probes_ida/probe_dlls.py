import struct, os, glob
p = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
d = open(p, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe+6)[0]
optsz = struct.unpack_from('<H', d, pe+20)[0]
magic = struct.unpack_from('<H', d, pe+24)[0]
print('PE magic = 0x%X (0x20B = PE32+)' % magic)
# 数据目录：导入表是第 1 项（index 1）
ddoff = pe + 24 + (112 if magic == 0x20B else 96)
imp_rva, imp_size = struct.unpack_from('<II', d, ddoff + 1*8)
print('导入表 RVA = 0x%X  size = %d' % (imp_rva, imp_size))
secs = []
off = pe + 24 + optsz
for i in range(nsec):
    b = d[off+i*40: off+i*40+40]
    name = b[:8].rstrip(b'\x00').decode('latin1')
    vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
    secs.append((name, vaddr, vsize, raw, rsize))
def rva2off(rva):
    for name, vaddr, vsize, raw, rsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return raw + (rva - vaddr)
    return None
print('')
print('=== hoi4.exe 导入的 DLL ===')
o = rva2off(imp_rva)
i = 0
while True:
    ent = d[o + i*20: o + i*20 + 20]
    if len(ent) < 20 or ent == b'\x00'*20:
        break
    name_rva = struct.unpack_from('<I', ent, 12)[0]
    if name_rva == 0:
        break
    no = rva2off(name_rva)
    nm = d[no:no+64].split(b'\x00')[0].decode('latin1')
    print('   %s' % nm)
    i += 1
    if i > 60: break
print('')
print('=== 游戏根目录下的 .dll ===')
root = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
for f in sorted(glob.glob(os.path.join(root, '*.dll'))):
    print('   %-36s %8.1f KB' % (os.path.basename(f), os.path.getsize(f)/1024))
print('')
print('=== 关键子目录 ===')
for sub in ['steam_settings', 'EmptySteamDepot', 'pdx_launcher']:
    fp = os.path.join(root, sub)
    if os.path.isdir(fp):
        fs = os.listdir(fp)[:12]
        print('   %s/ -> %s' % (sub, ', '.join(fs)))
    else:
        print('   %s/ -> (不存在)' % sub)
print('')
print('=== mod 目录情况 ===')
for cand in [os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive', 'Hearts of Iron IV', 'mod'),
             os.path.join(root, 'mod')]:
    print('   %s -> %s' % (cand, 'EXISTS' if os.path.isdir(cand) else 'no'))
    if os.path.isdir(cand):
        for x in sorted(os.listdir(cand))[:15]:
            print('        ', x)
