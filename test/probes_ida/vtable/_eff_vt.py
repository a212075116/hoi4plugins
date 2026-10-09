import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
def vt(ea, label, n=8):
    print('=== %s @ %#x ===' % (label, ea))
    for i in range(n):
        r = send({'op':'bytes','ea':hex(ea + i*8),'n':8})
        h = r.get('hex')
        if not h: break
        p = int.from_bytes(bytes.fromhex(h), 'little')
        if p == 0: break
        f = send({'op':'func','ea':hex(p)})
        nm = f.get('name') or '?'; sz = f.get('size')
        print('   [%d] +0x%02X  %#x  %-28s size=%s' % (i, i*8, p - IMG, nm, sz))
    print()
vt(0x14277ced8, 'CEffectEntry<CAddStabilityEffect> vftable')
vt(0x14276edf8, 'CAddStabilityEffect vftable')
print('=== 对照: 另一个 effect 的 entry 虚表 (add_manpower) ===')
n = send({'op':'names','needle':'CEffectEntry@VCAddManpowerEffect','limit':5})
for it in (n.get('items') or [])[:3]: print('   %s  %s' % (it['ea'], it['name']))
