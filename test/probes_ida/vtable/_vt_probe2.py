import sys, json
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== 0x142969118 附近 (往前 20 个槽) ===')
base = 0x142969118 - 20*8
for i in range(-20, 12):
    ea = 0x142969118 + i*8
    b = send({'op':'bytes','ea':hex(ea),'n':8})
    h = b.get('hex')
    if not h: print('  %#x  ??' % ea); continue
    v = int.from_bytes(bytes.fromhex(h), 'little')
    nm = send({'op':'names','needle':hex(v)[2:],'limit':1}) if False else None
    mark = '  <<< sub_140DC53B0' if v == 0x140DC53B0 else ''
    print('  %#x  槽[%+3d] = %#018x%s' % (ea, i, v, mark))
print()
print('=== sub_140DC53B0 的反编译 (确认它就是 cam getter) ===')
r = send({'op':'decompile','ea':'0x140DC53B0','lines':20})
print(r.get('text') if r.get('ok') else str(r.get('err')))
