import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send

print('=' * 78)
print('=== sub_1417CCC80 (调 150 与 2A0, 疑似滚轮) ===')
print('=' * 78)
r = send({'op':'decompile','ea':'0x1417CCC80','lines':70})
print(r.get('text'))
print()
print('=' * 78)
print('=== 一个调用者 sub_140280E90 里, 传给 3F0 的 a2 是什么 ===')
print('=' * 78)
r2 = send({'op':'decompile','ea':'0x140280E90','lines':90})
t = r2.get('text') or ''
ls = t.split(chr(10))
for i, l in enumerate(ls):
    if 'sub_1412643F0' in l or '12643F0' in l:
        for j in range(max(0, i-6), min(len(ls), i+3)):
            print('  %s' % ls[j])
        print('  ---')
