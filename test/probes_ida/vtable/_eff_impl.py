import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== +0x38 子类实现 sub_140378500 (533B) ===')
r = send({'op':'decompile','ea':'0x140378500','lines':95})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x140378500','count':45,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== 基类默认实现 sub_1401773F0 (34B) ===')
r2 = send({'op':'decompile','ea':'0x1401773F0','lines':15})
t2 = r2.get('text')
if t2: print(t2)
else:
    d2 = send({'op':'disasm','ea':'0x1401773F0','count':12,'back':0})
    s2 = d2.get('text') or d2.get('lines') or ''
    print(s2 if isinstance(s2,str) else chr(10).join(s2))
