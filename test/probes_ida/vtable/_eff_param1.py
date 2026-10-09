import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
f = send({'op':'func','ea':'0x140544C90'})
print('sub_140544C90: size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x140544C90','lines':70})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x140544C90','count':40,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
