import struct, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'

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
        nm = b[:8].rstrip(b'\x00').decode('latin1')
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
        secs.append((nm, vaddr, vsize, raw, rsize))
    def r2o(rva):
        for nm, vaddr, vsize, raw, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raw + (rva - vaddr)
        return None
    def walk(diridx, is_export):
        rva, size = struct.unpack_from('<II', d, ddoff + diridx*8)
        if not rva: return []
        o = r2o(rva)
        if o is None: return []
        res = []
        if is_export:
            # IMAGE_EXPORT_DIRECTORY: Name(RVA) at +0x0C
            nr = struct.unpack_from('<I', d, o + 0x0C)[0]
            no = r2o(nr)
            if no: res.append(d[no:no+64].split(b'\x00')[0].decode('latin1'))
            return res
        i = 0
        while i < 300:
            ent = d[o+i*20: o+i*20+20]
            if len(ent) < 20 or ent == b'\x00'*20: break
            nr = struct.unpack_from('<I', ent, 12)[0]
            if not nr: break
            no = r2o(nr)
            if no is None: break
            res.append(d[no:no+64].split(b'\x00')[0].decode('latin1'))
            i += 1
        return res
    return walk(0, True), walk(1, False)

names = ['Juij_Steam.dll', 'version.dll', 'winmm.dll', 'winhttp.dll',
         'steam_api64.dll', 'steam_api64_o.dll', 'PDXSDK.dll', 'tbb.dll']
for nm in names:
    fp = os.path.join(root, nm)
    if not os.path.exists(fp): 
        print('%-24s <缺失>' % nm); continue
    exp, imp = parse(fp)
    print('%-24s %8.1f KB  导出名=%s  导入数=%d' % (nm, os.path.getsize(fp)/1024, exp[0] if exp else '-', len(imp)))
    if imp:
        print('        导入: %s' % ', '.join(imp[:10]))
