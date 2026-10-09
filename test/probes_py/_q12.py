import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea in ['0x1433A8320', '0x1433A8368', '0x1433A8488']:
    x = send({'op':'xrefs_to','ea':ea})
    print('=== effect 表项 %s 引用数=%s ===' % (ea, x.get('count')))
    for rf in (x.get('refs') or [])[:12]:
        print('   %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
    print()
# 看这块内存是不是连续的表
r = send({'op':'bytes','ea':'0x1433A8320','n':16})
print('1433A8320 前16字节:', r.get('hex'))
r2 = send({'op':'bytes','ea':'0x1433A8368','n':16})
print('1433A8368 前16字节:', r2.get('hex'))
