import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
f = send({'op':'func','ea':'0x1424BB460'})
print('sub_1424BB460: size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x1424BB460','lines':40})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x1424BB460','count':28,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== 调用点 0x1424BB4E0 的上下文 ===')
d2 = send({'op':'disasm','ea':'0x1424BB4E0','count':3,'back':12})
t2 = d2.get('text') or d2.get('lines') or ''
print(t2 if isinstance(t2,str) else chr(10).join(t2))
