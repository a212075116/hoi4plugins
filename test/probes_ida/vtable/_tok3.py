import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== sub_1400831C0 的调用者 (谁初始化 token 表) ===')
x = send({'op':'xrefs_to','ea':'0x1400831C0'})
print('  被引用 %s 处' % x.get('count'))
for rf in (x.get('refs') or [])[:10]:
    print('    %s  in %s' % (rf['from'], rf['func']))
print()
print('=== sub_1400831C0 结尾 ===')
END = 0x1400831C0 + 613567
d = send({'op':'disasm','ea':hex(END - 120),'count':24,'back':0})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
