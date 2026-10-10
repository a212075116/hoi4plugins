import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
for ea, nm in [('0x1424C4B70','sub_1424C4B70 (注册函数)'), ('0x14014BD50','sub_14014BD50 (取id)')]:
    f = send({'op':'func','ea':ea})
    print('=' * 76)
    print('%s  size=%s' % (nm, f.get('size')))
    print('=' * 76)
    r = send({'op':'decompile','ea':ea,'lines':60})
    t = r.get('text')
    if t:
        print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':40,'back':0})
        tt = d.get('text') or d.get('lines') or ''
        print(tt if isinstance(tt,str) else chr(10).join(tt))
    print()
