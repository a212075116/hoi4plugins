import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
x = send({'op':'xrefs_to','ea':'0x1424C4B70'})
refs = x.get('refs') or []
print('总引用 %d' % len(refs))
print()
# 取若干不同调用点, 反汇编看 rcx 怎么算出来的
picks = [refs[i]['from'] for i in [0, 1, 3, 50, 500, 3000, 8000, 10000] if i < len(refs)]
for a in picks:
    ea = int(a, 16)
    d = send({'op':'disasm','ea':hex(ea),'count':4,'back':6})
    t = d.get('text') or d.get('lines') or ''
    ls = t.split(chr(10)) if isinstance(t,str) else list(t)
    print('--- call @ %s ---' % a)
    for l in ls: print('    ' + l)
    print()
