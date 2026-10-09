import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x1410E10C0','sub_1410E10C0 (capture_commander 用它处理 data[0])'),
                  ('0x1424B5CC0','sub_1424B5CC0 (按名字查命令)')]:
    f = send({'op':'func','ea':ea})
    r = send({'op':'decompile','ea':ea,'lines':45})
    t = r.get('text') if r.get('ok') else ('ERR ' + str(r.get('err')))
    print('=' * 80)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 80)
    print(chr(10).join(t.split(chr(10))[:42]))
    print()
