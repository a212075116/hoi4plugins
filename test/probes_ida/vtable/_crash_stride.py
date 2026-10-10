import sys, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x1424B5EF0','lines':400})
t = r.get('text') or ''
ls = t.split(chr(10))
print('总行数: %d' % len(ls))
print()
print('=== 含 v21 的行 ===')
for i, l in enumerate(ls):
    if 'v21' in l:
        print('%4d: %s' % (i, l))
print()
print('=== 含 v22 的行 ===')
for i, l in enumerate(ls):
    if 'v22' in l:
        print('%4d: %s' % (i, l))
print()
print('=== 循环收尾 (while v28) 附近 ===')
for i, l in enumerate(ls):
    if 'while' in l and ('v28' in l or 'v8' in l):
        for j in range(max(0,i-3), min(len(ls), i+4)):
            print('%4d: %s' % (j, ls[j]))
        print('---')
