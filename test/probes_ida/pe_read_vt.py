import struct
p = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
d = open(p, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe+6)[0]
optsz = struct.unpack_from('<H', d, pe+20)[0]
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
def u32(rva):
    o = rva2off(rva)
    return struct.unpack_from('<I', d, o)[0] if o is not None else None
def u64(rva):
    o = rva2off(rva)
    return struct.unpack_from('<Q', d, o)[0] if o is not None else None
def rtti_name(col_rva):
    sig = u32(col_rva)
    td = u32(col_rva + 0x0C)
    o = rva2off(td)
    nm = d[o+0x10:o+0x10+80].split(b'\x00')[0].decode('latin1','replace')
    return sig, td, nm
for RVA, label in [(0x29530D8, 'CUnit main'), (0x29532B0, 'CUnit _0'), (0x2953320, 'CUnit _1')]:
    print('=' * 60)
    print('RVA 0x%X  (%s)' % (RVA, label))
    col = u64(RVA - 8)
    print('  [RVA-8] COL = 0x%X' % col)
    if col:
        sig, td, nm = rtti_name(col - 0x140000000)
        print('    COL sig=%d  TypeDescriptor=0x%X  name=%s' % (sig, td, nm))
    print('  槽位:')
    for k in range(24):
        v = u64(RVA + k*8)
        print('    [%2d] 0x%X' % (k, v))
    print()
