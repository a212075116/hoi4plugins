import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x140540EE0','lines':200})
t = r.get('text') or ''
ls = t.split(chr(10))
print('总行数 %d, 打印 60..150' % len(ls))
print(chr(10).join(ls[60:150]))
