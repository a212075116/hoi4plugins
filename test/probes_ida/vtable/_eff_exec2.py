import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
for ea, nm in [('0x14053D7F0','+0xA8 执行')]:
    print('=' * 74)
    print('%s  @ %s' % (nm, ea))
    print('=' * 74)
    r = send({'op':'decompile','ea':ea,'lines':45})
    t = r.get('text')
    if t: print(t)
    else:
        d = send({'op':'disasm','ea':ea,'count':35,'back':0})
        s = d.get('text') or d.get('lines') or ''
        print(s if isinstance(s,str) else chr(10).join(s))
    print()
print('=== 对照 +0xB0 sub_14053D750 ===')
r2 = send({'op':'decompile','ea':'0x14053D750','lines':40})
t2 = r2.get('text')
if t2: print(t2)
else:
    d2 = send({'op':'disasm','ea':'0x14053D750','count':30,'back':0})
    s2 = d2.get('text') or d2.get('lines') or ''
    print(s2 if isinstance(s2,str) else chr(10).join(s2))
