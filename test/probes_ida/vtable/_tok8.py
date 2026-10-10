import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
f = send({'op':'func','ea':'0x142703050'})
print('sub_142703050: size=%s' % f.get('size'))
r = send({'op':'decompile','ea':'0x142703050','lines':45})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x142703050','count':30,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
print()
print('=== 表范围确认 ===')
lo = 0x14338D170; hi = 0x14344A518
print('  表首 %#x  表尾 %#x  差 %d  除以 72 = %.4f' % (lo, hi, hi-lo, (hi-lo)/72))
print('  add_stability 槽 %#x -> 索引 %d' % (0x1433A7630, (0x1433A7630-lo)//72))
print()
print('=== sub_14206CDC0 / sub_14206CE70 的调用者 ===')
for ea in ['0x14206CDC0','0x14206CE70']:
    x = send({'op':'xrefs_to','ea':ea})
    print('  %s 被引用 %s 处' % (ea, x.get('count')))
    for rf in (x.get('refs') or [])[:6]:
        print('      %s  in %s' % (rf['from'], rf['func']))
