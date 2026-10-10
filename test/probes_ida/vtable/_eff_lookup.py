import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== qword_143330000 (_EffectEntries) 的引用 ===')
x = send({'op':'xrefs_to','ea':'0x143330000'})
print('  引用 %s 处' % x.get('count'))
for rf in (x.get('refs') or [])[:20]:
    print('    %s  in %s' % (rf['from'], rf['func']))
print()
print('=== sub_140540EE0 (CAddStabilityEffect 最大虚函数, 1726B) 头部 ===')
r = send({'op':'decompile','ea':'0x140540EE0','lines':45})
t = r.get('text')
if t: print(t)
else:
    d = send({'op':'disasm','ea':'0x140540EE0','count':40,'back':0})
    s = d.get('text') or d.get('lines') or ''
    print(s if isinstance(s,str) else chr(10).join(s))
