import struct
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
d = open(p,'rb').read()
e = struct.unpack_from('<I', d, 0x3c)[0]
assert d[e:e+4] == b'PE\x00\x00'
nsec = struct.unpack_from('<H', d, e+6)[0]
optsz = struct.unpack_from('<H', d, e+20)[0]
opt = e + 24
magic = struct.unpack_from('<H', d, opt)[0]
print('magic=%#x nsec=%d optsz=%d' % (magic, nsec, optsz))
sec = opt + optsz
secs = []
for i in range(nsec):
    off = sec + i*40
    raw = d[off:off+8]
    nm = raw.split(b'\x00')[0].decode('latin1')
    vsz, va, rsz, ra = struct.unpack_from('<IIII', d, off+8)
    secs.append((nm, va, vsz, ra, rsz))
    print('  %-10s va=%#010x vsz=%#x  ra=%#x rsz=%#x' % (nm, va, vsz, ra, rsz))

def f2r(fo):
    for nm, va, vsz, ra, rsz in secs:
        if ra <= fo < ra + rsz:
            return va + (fo - ra)
    return None

targets = {
  'GetOccupationLaw': 0x297cb37,
  'no_occupatin_data': 0x297cb4d,
  'resistance_cpp': 0x297ca10,
}
print()
for k, fo in targets.items():
    rva = f2r(fo)
    print('%-22s fileoff=%#x -> RVA=%#x  (VA=%#x)' % (k, fo, rva, rva + 0x140000000))
