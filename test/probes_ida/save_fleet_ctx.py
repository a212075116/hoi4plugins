import re, collections
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/ABY_500_01_01_01.hoi4'
b = open(p, 'rb').read()
print('=== fleet 出现处的上下文(前后 40 字节的可打印部分), 前 30 个 ===')
ctx = []
for m in re.finditer(rb'fleet', b):
    s = max(0, m.start()-40); e = min(len(b), m.start()+60)
    seg = b[s:e]
    ctx.append(''.join(chr(c) if 32 <= c < 127 else '.' for c in seg))
print('总出现次数: %d' % len(ctx))
seen = set()
n = 0
for c in ctx:
    key = c[30:60]
    if key in seen: continue
    seen.add(key)
    print('   %s' % c)
    n += 1
    if n >= 30: break
print('')
print('=== 去重后的 fleet 上下文种类数: %d ===' % len(seen))
print('')
print('=== 找 reserve(预备舰队) / navy 关键字 ===')
for kw in (b'reserve', b'RESERVE', b'navy', b'Navy', b'NAVY', b'Fleet', b'FLEET_NAME'):
    print('   %-14r x%d' % (kw, b.count(kw)))