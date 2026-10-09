import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
for nm, ea in [('unk_1433A7630 (add_stability 槽)', '0x1433A7630'),
               ('unk_1433A75E8 (add_legitimacy 槽)', '0x1433A75E8'),
               ('unk_1433A75A0 (unlock_subunit 槽)', '0x1433A75A0')]:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== %s  引用 %s 处 ===' % (nm, x.get('count')))
    for rf in (x.get('refs') or [])[:8]:
        print('    %s  in %s' % (rf['from'], rf['func']))
    print()
