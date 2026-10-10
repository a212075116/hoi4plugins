import struct, re
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/autosave.hoi4'
d = open(p, 'rb').read()
print('文件: %d 字节' % len(d), flush=True)

# 1) 搜相邻的 int32 (50, 4000) = +0x6D0/+0x6D4
pat = struct.pack('<ii', 50, 4000)
pos = [m.start() for m in re.finditer(re.escape(pat), d)]
print('相邻 int32 (50,4000) 出现次数: %d' % len(pos), flush=True)
for off in pos[:10]:
    print('  偏移 0x%X: %s' % (off, d[max(0,off-16):off+24].hex(' ')), flush=True)

# 2) 也试 float (50.0, 4000.0)
patf = struct.pack('<ff', 50.0, 4000.0)
posf = [m.start() for m in re.finditer(re.escape(patf), d)]
print('相邻 float (50.0,4000.0) 出现次数: %d' % len(posf), flush=True)

# 3) 搜摄像机对象里的其它特征: (3264.0, 312.0, 760.0) 那组预设常量
patc = struct.pack('<fff', 3264.0, 312.0, 760.0)
posc = [m.start() for m in re.finditer(re.escape(patc), d)]
print('构造函数预设常量 (3264,312,760) 出现次数: %d' % len(posc), flush=True)
for off in posc[:5]:
    print('  偏移 0x%X: %s' % (off, d[max(0,off-8):off+32].hex(' ')), flush=True)
