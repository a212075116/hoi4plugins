import struct

def scan(path, crash_addr=None):
    d = open(path, 'rb').read()
    nstreams, sdir = struct.unpack_from('<II', d, 8)
    streams = {}
    for i in range(nstreams):
        t, sz, r = struct.unpack_from('<III', d, sdir + i*12)
        if sz: streams[t] = (sz, r)
    # ModuleListStream = 4
    msz, mr = streams[4]
    nmod = struct.unpack_from('<I', d, mr)[0]
    mods = []
    for i in range(nmod):
        b = mr + 4 + i*108
        base = struct.unpack_from('<Q', d, b + 0)[0]      # BaseOfImage @ +0
        size = struct.unpack_from('<I', d, b + 8)[0]      # SizeOfImage @ +8
        namerva = struct.unpack_from('<I', d, b + 20)[0]  # ModuleNameRva @ +20
        ln = struct.unpack_from('<I', d, namerva)[0]
        nm = d[namerva+4:namerva+4+ln].decode('utf-16-le', 'ignore')
        mods.append((base, size, nm))
    return d, streams, mods

import os
base_dir = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crashes'
cases = [
    ('hoi4_20261009_212722', 0x00007FF6F4E645C6),
    ('hoi4_20261009_234318', 0x00007FF6C706BF4B),
    ('hoi4_20261010_173105', None),
]
for name, addr in cases:
    dmp = os.path.join(base_dir, name, 'minidump.dmp')
    if not os.path.exists(dmp):
        print('=== %s: 无 minidump ===' % name, flush=True); continue
    d, streams, mods = scan(dmp)
    hi = None
    for base, size, nm in mods:
        if nm.lower().endswith('hoi4.exe'):
            hi = (base, size, nm); break
    print('=== %s ===' % name, flush=True)
    print('  模块数 %d' % len(mods), flush=True)
    if hi:
        base, size, nm = hi
        print('  hoi4.exe base=0x%X size=0x%X' % (base, size), flush=True)
        if addr:
            print('  崩溃地址 0x%X  =>  RVA 0x%X' % (addr, addr - base), flush=True)
        else:
            print('  (本次崩溃地址从 exception.txt 取: Pure Virtual Function Call)', flush=True)
    else:
        print('  未找到 hoi4.exe 模块', flush=True)
    # 也列出我们插件的模块
    for base, size, nm in mods:
        n = nm.lower()
        if 'plugin' in n or 'tbb' in n:
            print('  相关模块: 0x%X 0x%X %s' % (base, size, nm), flush=True)
