import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== +0x38 子类实现 sub_140378500 完整 (533B) ===')
r = send({'op':'decompile','ea':'0x140378500','lines':120})
t = r.get('text') or ''
print(t)
print()
print('=== sub_142245E60 (构造 key+参数对象) ===')
f = send({'op':'func','ea':'0x142245E60'})
print('size=%s' % f.get('size'))
r2 = send({'op':'decompile','ea':'0x142245E60','lines':30})
t2 = r2.get('text')
if t2: print(t2)
else:
    d = send({'op':'disasm','ea':'0x142245E60','count':20,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
