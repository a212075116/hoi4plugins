import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x1424BC310','lines':75})
t = r.get('text')
print('=== CLexer::? sub_1424BC310 (1756B) ===')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x1424BC310','count':45,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
