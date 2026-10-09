import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== sub_1405415A0 (注册函数) ===')
f = send({'op':'func','ea':'0x1405415A0'})
print('size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x1405415A0','lines':80})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x1405415A0','count':50,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== CEffectEntry<CAddStabilityEffect> 的虚表 (查符号) ===')
n = send({'op':'names','needle':'CEffectEntry@VCAddStabilityEffect','limit':20})
for it in (n.get('items') or []):
    print('   %s  %s' % (it['ea'], it['name']))
print()
n2 = send({'op':'names','needle':'CAddStabilityEffect','limit':20})
print('=== CAddStabilityEffect 相关符号 ===')
for it in (n2.get('items') or []):
    print('   %s  %s' % (it['ea'], it['name']))
