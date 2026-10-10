import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
f = send({'op':'func','ea':'0x1401205A0'})
print('sub_1401205A0: size=%s start=%s' % (f.get('size'), f.get('start')))
r = send({'op':'decompile','ea':'0x1401205A0','lines':50})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x1401205A0','count':35,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== sub_140540EE0 的调用者 (找「谁执行 effect 列表」) ===')
x = send({'op':'xrefs_to','ea':'0x140540EE0'})
print('  被引用 %s 处' % x.get('count'))
seen = set()
for rf in (x.get('refs') or [])[:12]:
    print('    %s  in %s' % (rf['from'], rf['func']))
