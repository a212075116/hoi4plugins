import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for pat, label in [('call.*\\[.*\\+68h\\]', '间接调用 +0x68 (命令处理函数)'),
                   ('call.*\\[.*\\+0x68\\]', '间接调用 +0x68 (另一种写法)')]:
    r = send({'op':'grep_disasm','pat':pat,'limit':60})
    print('=== %s -> %s 命中 ===' % (label, r.get('count')))
    for h in (r.get('hits') or [])[:40]:
        print('   %s  %-46s  %s' % (h.get('ea'), h.get('text','')[:46], h.get('func')))
    print()
