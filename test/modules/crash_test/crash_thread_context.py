import struct

p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crashes/hoi4_20261010_173105/minidump.dmp'
d = open(p, 'rb').read()
nstreams, sdir = struct.unpack_from('<II', d, 8)
st = {}
for i in range(nstreams):
    t, sz, r = struct.unpack_from('<III', d, sdir + i*12)
    if sz: st[t] = (sz, r)
print('流:', sorted(st.keys()), flush=True)
msz, mr = st[4]
nmod = struct.unpack_from('<I', d, mr)[0]
mods = []
for i in range(nmod):
    b = mr + 4 + i*108
    bb = struct.unpack_from('<Q', d, b)[0]
    sz2 = struct.unpack_from('<I', d, b + 8)[0]
    nr = struct.unpack_from('<I', d, b + 20)[0]
    ln = struct.unpack_from('<I', d, nr)[0]
    nm = d[nr+4:nr+4+ln].decode('utf-16-le','ignore')
    mods.append((bb, sz2, nm))
base = [m[0] for m in mods if m[2].lower().endswith('hoi4.exe')][0]
print('hoi4.exe base=0x%X' % base, flush=True)

tsz, tr = st[3]
nth = struct.unpack_from('<I', d, tr)[0]
print('线程 %d, ThreadList 流大小 %d, 需要 %d' % (nth, tsz, 4 + nth*48), flush=True)

# 看第一个线程的原始 48 字节
off = tr + 4
raw = d[off:off+48]
print('', flush=True)
print('线程[0] 原始 48 字节:', flush=True)
for j in range(0, 48, 4):
    print('  +%02d: %s' % (j, raw[j:j+4].hex(' ')), flush=True)
tid = struct.unpack_from('<I', raw, 0)[0]
teb = struct.unpack_from('<Q', raw, 16)[0]
stk_addr = struct.unpack_from('<Q', raw, 24)[0]
stk_sz, stk_rva = struct.unpack_from('<II', raw, 32)
ctx_sz, ctx_rva = struct.unpack_from('<II', raw, 40)
print('', flush=True)
print('  ThreadId=0x%X (%d)' % (tid, tid), flush=True)
print('  Teb=0x%X' % teb, flush=True)
print('  Stack: addr=0x%X size=0x%X rva=0x%X' % (stk_addr, stk_sz, stk_rva), flush=True)
print('  Context: size=0x%X rva=0x%X' % (ctx_sz, ctx_rva), flush=True)
if ctx_rva and ctx_rva + 0x100 < len(d):
    blob = d[ctx_rva:ctx_rva+ctx_sz]
    print('', flush=True)
    print('  Context 前 0x100 字节里的可疑指针(RIP@0xF8, Rsp@0x98):', flush=True)
    rip = struct.unpack_from('<Q', blob, 0xF8)[0] if len(blob) > 0x100 else 0
    rsp = struct.unpack_from('<Q', blob, 0x98)[0] if len(blob) > 0xA0 else 0
    print('    Rip=0x%X  Rsp=0x%X' % (rip, rsp), flush=True)
    # 在 blob 里搜 hoi4.exe 范围内的地址
    hits = []
    for j in range(0, len(blob)-8, 8):
        v = struct.unpack_from('<Q', blob, j)[0]
        if base <= v < base + 0x37EC000: hits.append((j, v))
    print('    Context 内 hoi4.exe 地址: %d 个' % len(hits), flush=True)
    for j, v in hits[:10]:
        print('      +0x%03X = 0x%X (hoi4+0x%X)' % (j, v, v - base), flush=True)
