import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea in ['0x141260FB0','0x141261320','0x141261E70']:
    f = send({'op':'func','ea':ea})
    print('=' * 90)
    print('=== %s  %s  size=%s ===' % (ea, f.get('name'), f.get('size')))
    print('=' * 90)
    r = send({'op':'decompile','ea':ea,'lines':160})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
