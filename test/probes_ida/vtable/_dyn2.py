import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
for ea, nm in [('0x1424BC260','sub_1424BC260 (按id取名字)'), ('0x1424BB500','sub_1424BB500 (核心操作)')]:
    f = send({'op':'func','ea':ea})
    print('=' * 74)
    print('%s  size=%s' % (nm, f.get('size')))
    print('=' * 74)
    r = send({'op':'decompile','ea':ea,'lines':55})
    t = r.get('text')
    if t: print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':35,'back':0})
        s = d.get('text') or d.get('lines') or ''
        print(s if isinstance(s,str) else chr(10).join(s))
    print()
