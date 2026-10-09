import re, os, shutil
d = r'C:\\Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games'
src = os.path.join(d, 'VANILLA_1.hoi4')
dst = os.path.join(d, 'VANILLA_PATCHED.hoi4')
b = bytearray(open(src, 'rb').read())
OLD = b'1.19.0.0.5a1c'
NEW = b'1.19.3.0.c01a'
assert len(OLD) == len(NEW), (len(OLD), len(NEW))
pos = [m.start() for m in re.finditer(re.escape(OLD), bytes(b))]
print('旧版本串出现位置: %s' % [hex(x) for x in pos])
for x in pos:
    b[x:x+len(OLD)] = NEW
open(dst, 'wb').write(bytes(b))
print('写出 %s (%d 字节)' % (dst, len(b)))
b2 = open(dst, 'rb').read()
print('校验: 新版本串出现 %d 次, 旧版本串 %d 次' % (b2.count(NEW), b2.count(OLD)))