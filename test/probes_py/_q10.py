import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x140231DA0','128B, 引用 qword_14332F4F8 四次'), ('0x14022F7C0','8B, 引用一次'), ('0x1426F8000','136B, 引用三次')]:
    f = send({'op':'func','ea':ea})
    print('=' * 88)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 88)
    r = send({'op':'decompile','ea':ea,'lines':110})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
