import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
x = send({'op':'xrefs_to','ea':'0x1427298e0'})
print('=== debug_zoom 引用 (%s) ===' % x.get('count'))
for rf in (x.get('refs') or []):
    print('   %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
print()
if x.get('refs'):
    site = int(x['refs'][0]['from'], 16)
    print('=== 引用点前后 70 条指令 (从 %#x 开始) ===' % (site - 0x100))
    r = send({'op':'disasm','ea':hex(site - 0x100),'count':70})
    for ln in (r.get('lines') or []): print(ln)
