import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x1424B4920','注册进管理器 sub_1424B4920')]:
    f = send({'op':'func','ea':ea})
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    r = send({'op':'decompile','ea':ea,'lines':130})
    print(r.get('text') if r.get('ok') else str(r.get('err')))
    print()
print('=== qword_1435E1A80 的引用 ===')
x = send({'op':'xrefs_to','ea':'0x1435E1A80'})
print('引用数 =', x.get('count'))
for rf in (x.get('refs') or [])[:20]:
    print('   %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
