import struct, os

p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crashes/hoi4_20261010_173105/minidump.dmp'
d = open(p, 'rb').read()
nstreams, sdir = struct.unpack_from('<II', d, 8)
streams = {}
for i in range(nstreams):
    t, sz, r = struct.unpack_from('<III', d, sdir + i*12)
    if sz: streams[t] = (sz, r)
msz, mr = streams[4]
nmod = struct.unpack_from('<I', d, mr)[0]
base = None
for i in range(nmod):
    b = mr + 4 + i*108
    bb = struct.unpack_from('<Q', d, b)[0]
    namerva = struct.unpack_from('<I', d, b + 20)[0]
    ln = struct.unpack_from('<I', d, namerva)[0]
    nm = d[namerva+4:namerva+4+ln].decode('utf-16-le','ignore')
    if nm.lower().endswith('hoi4.exe'): base = bb
print('hoi4.exe base = 0x%X' % base, flush=True)
pure = base + 0x253C3B8
print('_purecall     = 0x%X' % pure, flush=True)

# 在全部内存里搜 purecall 的地址 (作为 RIP 或栈上的返回地址)
mlsz, mlr = streams[5]
nmem = struct.unpack_from('<I', d, mlr)[0]
segs = []
for i in range(nmem):
    off = mlr + 4 + i*16
    sa = struct.unpack_from('<Q', d, off)[0]
    sz, mrva = struct.unpack_from('<II', d, off + 8)
    segs.append((sa, sz, mrva))
print('内存段: %d' % len(segs), flush=True)
pat = struct.pack('<Q', pure)
found = []
for sa, sz, mrva in segs:
    blob = d[mrva:mrva+sz]
    idx = blob.find(pat)
    while idx >= 0:
        found.append((sa + idx, sa, sz))
        idx = blob.find(pat, idx + 1)
print('', flush=True)
print('=== 命中 _purecall 地址的位置: %d ===' % len(found), flush=True)
for a, seg_a, seg_sz in found[:20]:
    print('  0x%X  (段 0x%X size 0x%X)' % (a, seg_a, seg_sz), flush=True)
