import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x142753068','set_variable 的 ID'), ('0x1429B65E4','random 的 ID')]:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== %s (%s) 引用数=%s ===' % (ea, label, x.get('count')))
    for rf in (x.get('refs') or [])[:15]:
        print('   %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
    print()
    r = send({'op':'bytes','ea':ea,'n':16})
    print('   值:', r.get('hex'))
    print()
