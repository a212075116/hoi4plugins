import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for pat in ['+68h]', '+0x68]']:
    r = send({'op':'grep_disasm','pattern':pat,'limit':80})
    print('=== pattern %r -> count=%s ===' % (pat, r.get('count')))
    for h in (r.get('hits') or [])[:50]:
        print('   %-12s %-48s %s' % (h.get('ea'), (h.get('text') or '')[:48], h.get('func')))
    print()
