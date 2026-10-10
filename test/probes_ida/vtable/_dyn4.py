import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== sub_1424BB500 的调用者 ===')
x = send({'op':'xrefs_to','ea':'0x1424BB500'})
print('  被引用 %s 处' % x.get('count'))
for rf in (x.get('refs') or [])[:10]:
    print('    %s  in %s' % (rf['from'], rf['func']))
print()
print('=== 结尾 30 行 (返回值处理) ===')
r = send({'op':'decompile','ea':'0x1424BB500','lines':200})
t = r.get('text') or ''
ls = t.split(chr(10))
print(chr(10).join(ls[145:200]))
