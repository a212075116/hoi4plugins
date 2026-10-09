import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
for nm, ea in [('dword_1427529A0 (add_stability id)', '0x1427529A0'),
               ('dword_1427529A4 (add_manpower id)',  '0x1427529A4'),
               ('dword_14275299C (add_legitimacy id)','0x14275299C')]:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== %s  引用 %s 处 ===' % (nm, x.get('count')))
    for rf in (x.get('refs') or [])[:10]:
        print('    %s  in %s' % (rf['from'], rf['func']))
    print()
