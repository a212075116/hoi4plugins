import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== CAddStabilityEffect 虚表 +0x60 (sub_14053D9E0, 1865B) ===')
r = send({'op':'decompile','ea':'0x14053D9E0','lines':70})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x14053D9E0','count':40,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== 谁调 +0x60 (96) ? 查 sub_1406D23F0 是什么 ===')
f = send({'op':'func','ea':'0x1406D23F0'})
print('sub_1406D23F0: size=%s' % f.get('size'))
r2 = send({'op':'decompile','ea':'0x1406D23F0','lines':40})
t2 = r2.get('text')
if t2: print(t2)
else:
    d2 = send({'op':'disasm','ea':'0x1406D23F0','count':30,'back':0})
    s2 = d2.get('text') or d2.get('lines') or ''
    print(s2 if isinstance(s2,str) else chr(10).join(s2))
