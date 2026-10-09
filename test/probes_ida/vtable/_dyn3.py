import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x1424BB500','lines':160})
t = r.get('text') or ''
ls = t.split(chr(10))
print('总行 %d' % len(ls))
print(chr(10).join(ls[38:145]))
