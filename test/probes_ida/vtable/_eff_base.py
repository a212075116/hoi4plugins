import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
n = send({'op':'names','needle':'CValueEffect@@6B@','limit':10})
print('=== CValueEffect 虚表符号 ===')
for it in (n.get('items') or []):
    print('   %s  %s' % (it['ea'], it['name']))
print()
n2 = send({'op':'names','needle':'CEffectBase@@6B@','limit':10})
print('=== CEffectBase 虚表符号 ===')
for it in (n2.get('items') or []):
    print('   %s  %s' % (it['ea'], it['name']))
print()
print('=== 找所有 effect 实例虚表里共同的函数 (前几个槽) ===')
for vt_ea, lbl in [(0x14276edf8,'CAddStabilityEffect'), ]:
    for i in range(4):
        r = send({'op':'bytes','ea':hex(vt_ea+i*8),'n':8})
        p = int.from_bytes(bytes.fromhex(r['hex']),'little')
        f = send({'op':'func','ea':hex(p)})
        print('  %s [%d] +0x%02X -> %#x %s size=%s' % (lbl, i, i*8, p-IMG, f.get('name'), f.get('size')))
