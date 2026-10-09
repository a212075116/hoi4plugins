import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for nd in ['Unknown command', 'unknown command', 'nknown command', 'Usage:', 'usage:']:
    r = send({'op':'strings','needle':nd,'limit':8})
    print('=== %r -> %s ===' % (nd, r.get('count')))
    for it in (r.get('items') or []):
        print('   %s  %s' % (it['ea'], it['s'][:90]))
