import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x1424C4B70','注册函数 sub_1424C4B70'), ('0x14014BD50','换算 sub_14014BD50')]:
    f = send({'op':'func','ea':ea})
    print('=' * 90)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 90)
    r = send({'op':'decompile','ea':ea,'lines':120})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
