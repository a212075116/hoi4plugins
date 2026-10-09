import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== add_stability 描述字符串的引用点附近 (0x140018912) ===')
d = send({'op':'disasm','ea':'0x140018912','count':24,'back':16})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
print()
f = send({'op':'func','ea':'0x1400188E0'})
print('sub_1400188E0: size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x1400188E0','lines':70})
tt = r.get('text')
if tt:
    print(tt)
else:
    d2 = send({'op':'disasm','ea':'0x1400188E0','count':50,'back':0})
    s = d2.get('text') or d2.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
