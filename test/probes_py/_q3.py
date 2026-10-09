import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
import time
for pat in ['+6D4h', '+6D0h']:
    t = time.time()
    r = send({'op':'grep_disasm','pattern':pat,'limit':30}, timeout=900)
    print('=== grep %s  (扫描 %s 个函数, 用时 %.1fs) ===' % (pat, r.get('scanned_funcs'), time.time()-t))
    print('命中函数数 =', r.get('count'))
    for it in (r.get('items') or []):
        print('  %s @ %s  size=%s' % (it['func'], it['func_ea'], it['size']))
        for h in it['hits']:
            print('      %s  %s' % (h['ea'], h['d']))
    print()
