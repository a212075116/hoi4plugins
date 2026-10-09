import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
for ea, nm in [('0x14206CDC0','sub_14206CDC0'), ('0x14206CE70','sub_14206CE70')]:
    f = send({'op':'func','ea':ea})
    print('=' * 74)
    print('%s  size=%s' % (nm, f.get('size')))
    print('=' * 74)
    r = send({'op':'decompile','ea':ea,'lines':45})
    t = r.get('text')
    if t: print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':30,'back':0})
        s = d.get('text') or d.get('lines') or ''
        print(s if isinstance(s,str) else chr(10).join(s))
    print()
