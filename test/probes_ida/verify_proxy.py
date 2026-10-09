import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def dump_exports(path):
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
    erva = struct.unpack_from('<I', d, ddoff + 0*8)[0]
    o = r2o(erva)
    base = struct.unpack_from('<I', d, o + 0x10)[0]
    nfunc = struct.unpack_from('<I', d, o + 0x14)[0]
    nnames = struct.unpack_from('<I', d, o + 0x18)[0]
    funcptr = r2o(struct.unpack_from('<I', d, o + 0x1C)[0])
    nameptr = r2o(struct.unpack_from('<I', d, o + 0x20)[0])
    ordptr = r2o(struct.unpack_from('<I', d, o + 0x24)[0])
    fwd = []
    byord = {}
    for i in range(nnames):
        nr = struct.unpack_from('<I', d, nameptr + i*4)[0]
        no = r2o(nr)
        nm = d[no:no+128].split(b'\x00')[0].decode('latin1')
        ordi = struct.unpack_from('<H', d, ordptr + i*2)[0]
        fo_ = funcptr + ordi*4
        frva = struct.unpack_from('<I', d, fo_)[0]
        byord[ordi] = (nm, frva)
    # 找出落在导出目录范围内的 = 转发字符串
    exp_start, exp_end = erva, erva + struct.unpack_from('<I', d, ddoff + 0*8 + 4)[0]
    for ordi in sorted(byord):
        nm, frva = byord[ordi]
        if exp_start <= frva < exp_end:
            fo2 = r2o(frva)
            tgt = d[fo2:fo2+128].split(b'\x00')[0].decode('latin1')
            fwd.append((ordi, nm, tgt))
    return base, nfunc, nnames, fwd

p = 'work/proxy/dxgi.dll'
base, nfunc, nnames, fwd = dump_exports(p)
print('dxgi.dll 导出基数=%d  函数数=%d  名字数=%d' % (base, nfunc, nnames))
print('其中真·转发条目 = %d' % len(fwd))
print('')
for ordi, nm, tgt in fwd:
    print('   [%2d] %-34s -> %s' % (ordi, nm, tgt))
