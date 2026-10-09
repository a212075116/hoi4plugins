import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
cands = ['0x14011AAD0','0x14022D340','0x14022F570','0x140261A60','0x140261D10','0x1402A2570']
for ea in cands:
    f = send({'op':'func','ea':ea})
    r = send({'op':'decompile','ea':ea,'lines':45})
    t = r.get('text') if r.get('ok') else ('ERR ' + str(r.get('err')))
    print('=' * 80)
    print('=== %s  %s  size=%s ===' % (ea, f.get('name'), f.get('size')))
    print('=' * 80)
    print(t[:1800])
    print()
