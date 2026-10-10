import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
for ea, nm in [('0x1424C4D80','sub_1424C4D80 (分配字符串缓冲?)'),
               ('0x140145FD0','sub_140145FD0 (构造时调用)')]:
    f = send({'op':'func','ea':ea})
    print('=' * 74)
    print('%s  size=%s' % (nm, f.get('size')))
    print('=' * 74)
    r = send({'op':'decompile','ea':ea,'lines':40})
    t = r.get('text')
    if t: print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':28,'back':0})
        s = d.get('text') or d.get('lines') or ''
        print(s if isinstance(s,str) else chr(10).join(s))
    print()
print('=== sub_1424C4B70 的所有调用者数量 ===')
x = send({'op':'xrefs_to','ea':'0x1424C4B70'})
print('  被引用 %s 处' % x.get('count'))
for rf in (x.get('refs') or [])[:6]:
    print('    %s  in %s' % (rf['from'], rf['func']))
