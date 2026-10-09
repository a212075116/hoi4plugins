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
def r2f(rva):
    for nm, va, vsz, ra, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return ra + (rva - va)
    return None

# 引用点: lea rdx,[rip+disp] 的 disp 位于 rva; 指令起点 = disp_rva - 3
for dispRva, tag in [(0xf919ec, 'A'), (0xf99d93, 'B')]:
    insn = dispRva - 3           # 48 8d 15 <disp32>
    fo = r2f(insn)
    b = d[fo:fo+12]
    print('--- %s: lea 指令 rva=%#x  bytes=%s' % (tag, insn, ' '.join('%02x'%x for x in b)))
    # 往前找 call e8
    callRva = None
    for back in range(1, 24):
        f2 = r2f(insn - back)
        if d[f2] == 0xe8:
            rel = struct.unpack_from('<i', d, f2+1)[0]
            tgt = (insn - back) + 5 + rel
            callRva = insn - back
            print('    call @ rva=%#x -> rva=%#x  (VA=%#x)' % (callRva, tgt, tgt + 0x140000000))
            break
    if callRva is None:
        print('    (未找到紧邻的 call)')
