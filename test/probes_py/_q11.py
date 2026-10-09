import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x140231E20','批量追加 sub_140231E20'), ('0x14022BE10','表项析构 sub_14022BE10')]:
    f = send({'op':'func','ea':ea})
    print('=' * 88)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 88)
    r = send({'op':'decompile','ea':ea,'lines':90})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
