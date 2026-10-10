import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
f = send({'op':'func','ea':'0x1402F14B0'})
print('sub_1402F14B0: size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x1402F14B0','lines':60})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x1402F14B0','count':40,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== 该调用者附近, sub_140540EE0 是怎么被调的 (0x1402F14EB) ===')
d2 = send({'op':'disasm','ea':'0x1402F14EB','count':10,'back':14})
t2 = d2.get('text') or d2.get('lines') or ''
print(t2 if isinstance(t2,str) else chr(10).join(t2))
