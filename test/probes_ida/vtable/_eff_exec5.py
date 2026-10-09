import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
for ea, nm in [('0x14053F090','+0x40 (975B)'), ('0x14053F460','+0x50 (1562B)')]:
    print('=' * 74)
    print('%s  @ %s' % (nm, ea))
    print('=' * 74)
    r = send({'op':'decompile','ea':ea,'lines':55})
    t = r.get('text')
    if t: print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':40,'back':0})
        s = d.get('text') or d.get('lines') or ''
        print(s if isinstance(s,str) else chr(10).join(s))
    print()
