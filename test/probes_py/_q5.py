import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
# 1. 找 effect 名字符串
for needle in ['set_variable', 'add_country_flag', 'set_camera']:
    r = send({'op':'strings','needle':needle,'limit':10})
    print('=== strings %r -> %s ===' % (needle, r.get('count')))
    for it in (r.get('items') or []):
        print('   %s  %r' % (it['ea'], it['s'][:80]))
    print()
# 2. 找 set_variable 这个精确字符串的引用
r = send({'op':'strings','needle':'set_variable','limit':40})
exact = [it for it in (r.get('items') or []) if it['s'] == 'set_variable']
print('精确等于 set_variable 的字符串:', len(exact))
for it in exact[:4]:
    ea = int(it['ea'], 16)
    x = send({'op':'xrefs_to','ea':hex(ea)})
    print('  %s 引用数=%s' % (it['ea'], x.get('count')))
    for rf in (x.get('refs') or [])[:6]:
        print('      %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
