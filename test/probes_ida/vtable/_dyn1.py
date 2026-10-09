import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
for nm, ea in [('qword_1435E1AC0 (data)',  '0x1435E1AC0'),
               ('dword_1435E1ACC (count)', '0x1435E1ACC'),
               ('byte_1435E1AB0 (init?)',  '0x1435E1AB0'),
               ('qword_1435E1AD0 (alloc)', '0x1435E1AD0')]:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== %s  引用 %s 处 ===' % (nm, x.get('count')))
    seen = []
    for rf in (x.get('refs') or [])[:14]:
        fn = rf['func']
        if fn not in seen: seen.append(fn)
    for fn in seen[:10]:
        print('    in %s' % fn)
    print()
