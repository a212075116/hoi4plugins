import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea in ['0x140129CA0','0x140129C10','0x14011E1A0']:
    f = send({'op':'func','ea':ea})
    r = send({'op':'decompile','ea':ea,'lines':40})
    t = r.get('text') if r.get('ok') else ('ERR ' + str(r.get('err')))
    print('=' * 78)
    print('=== %s  %s  size=%s ===' % (ea, f.get('name'), f.get('size')))
    print('=' * 78)
    print(chr(10).join(t.split(chr(10))[:36]))
    print()
