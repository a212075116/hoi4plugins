import struct, os
ROOT = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
def parse(path):
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
    return d, r2o, ddoff

# hoi4.exe 的导入表：拿到 (dll名, 该dll的函数名列表)
d, r2o, ddoff = parse(os.path.join(ROOT, 'hoi4.exe'))
irva = struct.unpack_from('<I', d, ddoff + 8)[0]
o = r2o(irva)
entries = []
i = 0
while i < 400:
    ent = d[o+i*20: o+i*20+20]
    if len(ent) < 20 or ent == b'\x00'*20: break
    oft = struct.unpack_from('<I', ent, 0)[0]
    nr  = struct.unpack_from('<I', ent, 12)[0]
    if not nr: break
    no = r2o(nr)
    name = d[no:no+80].split(b'\x00')[0].decode('latin1')
    funcs = []
    if oft:
        oo = r2o(oft)
        if oo:
            j = 0
            while j < 2000:
                t = struct.unpack_from('<Q', d, oo + j*8)[0]
                if t == 0: break
                if not (t & (1 << 63)):   # 按序号导入
                    fnr = r2o((t & 0x7FFFFFFF))
                    if fnr: funcs.append(d[fnr:fnr+200].split(b'\x00')[0].decode('latin1'))
                    else: funcs.append('#ordinal')
                else:
                    funcs.append('#ordinal_%d' % (t & 0xFFFF))
                j += 1
    entries.append((name, funcs))
    i += 1

for want in ['tbb.dll', 'PDXSDK.dll', 'steam_api64.dll']:
    for nm, fs in entries:
        if nm.lower() == want.lower():
            print('=== hoi4.exe 从 %s 导入 %d 个函数 ===' % (nm, len(fs)))
            for x in fs:
                print('   ', x)
            print()
            break
