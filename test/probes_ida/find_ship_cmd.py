import re
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
b = open(p, 'rb').read()
print('exe 大小: %d' % len(b))
print('')
needles = [b'create a ship from another country', b'reserve fleet', b'FLEET_NAME_NOT_SET', b'spawn_ship', b'create_ship', b'add_ship']
for nd in needles:
    idxs = [m.start() for m in re.finditer(re.escape(nd), b)]
    print('%-40r x%d  %s' % (nd, len(idxs), [hex(i) for i in idxs[:6]]))
print('')
i = b.find(b'create a ship from another country')
if i >= 0:
    s = max(0, i - 900); e = min(len(b), i + 400)
    seg = b[s:e]
    print('=== 上下文(前后, 取可打印字符串) ===')
    for m in re.finditer(rb'[ -~]{6,}', seg):
        print('   off=%+#x  %r' % (m.start() + s, m.group()[:150]))