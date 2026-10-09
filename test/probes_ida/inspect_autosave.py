import re
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/autosave.hoi4'
b = open(p, 'rb').read()
print('大小: %d' % len(b))
print('头部: %r' % b[:40])
print('')
print('=== task_force 上下文(前 12 个) ===')
n = 0; seen = set()
for m in re.finditer(rb'task_force', b):
    s = max(0, m.start()-60); e = min(len(b), m.start()+90)
    seg = ''.join(chr(c) if 32 <= c < 127 else '.' for c in b[s:e])
    if seg[50:80] in seen: continue
    seen.add(seg[50:80])
    print('   %s' % seg)
    n += 1
    if n >= 12: break
print('')
print('=== 是否有舰队名字样(FLEET_NAME / 1st Fleet 等) ===')
for kw in (b'FLEET_NAME_NOT_SET', b'fleet_name', b'_fleet', b'Fleet'):
    print('   %-20r x%d' % (kw, b.count(kw)))
print('')
print('=== 开头 1200 字节的可打印部分(看 mod 列表) ===')
print(''.join(chr(c) if 32 <= c < 127 else '.' for c in b[:1200]))