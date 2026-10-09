import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x142733ba0','Usage: capture_commander ...'),
                  ('0x142735900','Usage: bop_set <ID>'),
                  ('0x1427d5fc0',"unknown command '")]:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== %s  -> %s 处引用 ===' % (label, x.get('count')))
    for rf in (x.get('refs') or [])[:8]:
        print('    %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
    print()
# 找 capture_commander 命令名字符串
for nd in ['capture_commander','bop_set']:
    r = send({'op':'strings','needle':nd,'limit':5})
    print('=== 字符串 %r ===' % nd)
    for it in (r.get('items') or []): print('   %s  %s' % (it['ea'], it['s'][:80]))
