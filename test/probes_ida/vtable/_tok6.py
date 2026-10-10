import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
slots = ['0x14338D170','0x14338D1B8','0x14338D248','0x1433A7630','0x14344A4D0']
for s in slots:
    x = send({'op':'xrefs_to','ea':s})
    print('=== %s  引用 %s 处 ===' % (s, x.get('count')))
    for rf in (x.get('refs') or [])[:6]:
        print('    %s  in %s' % (rf['from'], rf['func']))
    print()
