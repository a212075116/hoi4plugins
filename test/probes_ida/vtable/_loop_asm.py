import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== 崩溃循环的完整汇编 (0x1424B6391 - 0x1424B6410) ===')
d = send({'op':'disasm','ea':'0x1424B6391','count':40,'back':0})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
