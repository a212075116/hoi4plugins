import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SYS32 = os.path.join(os.environ['SystemRoot'], 'System32')

def exports(path):
    d = open(path, 'rb').read()
    if d[:2] != b'MZ': return []
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    if d[pe:pe+4] != b'PE\x00\x00': return []
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
    if not erva: return []
    o = r2o(erva)
    nnames = struct.unpack_from('<I', d, o + 0x18)[0]
    nameptr = struct.unpack_from('<I', d, o + 0x20)[0]
    npo = r2o(nameptr)
    res = []
    for i in range(nnames):
        nr = struct.unpack_from('<I', d, npo + i*4)[0]
        no = r2o(nr)
        res.append(d[no:no+128].split(b'\x00')[0].decode('latin1'))
    return res

TARGETS = ['d3d11.dll', 'dxgi.dll', 'imm32.dll', 'version.dll', 'winmm.dll', 'd3d9.dll']
info = {}
for t in TARGETS:
    p = os.path.join(SYS32, t)
    if not os.path.exists(p):
        print('%-14s <缺失>' % t); continue
    ex = exports(p)
    info[t] = ex
    print('%-14s 导出 %3d 个   %s' % (t, len(ex), ', '.join(ex[:4])))
print('')
os.makedirs('work/proxy', exist_ok=True)
for t, ex in info.items():
    base = t.split('.')[0]
    lines = ['LIBRARY %s' % base, 'EXPORTS']
    for e in ex:
        if e.startswith('?'):
            continue
        lines.append('    %s=%s_real.%s' % (e, base, e))
    fp = 'work/proxy/%s_proxy.def' % base
    open(fp, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('生成 %-34s %d 行' % (fp, len(lines)))
