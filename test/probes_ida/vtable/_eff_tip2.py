import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x142245E60','lines':80})
t = r.get('text') or ''
ls = t.split(chr(10))
print('=== sub_142245E60 全文 (%d 行) ===' % len(ls))
print(chr(10).join(ls[22:75]))
print()
print('=== sub_1410E48A0 签名 ===')
f = send({'op':'func','ea':'0x1410E48A0'})
print('size=%s' % f.get('size'))
r2 = send({'op':'decompile','ea':'0x1410E48A0','lines':30})
t2 = r2.get('text')
if t2: print(t2)
