import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'grep_disasm','pattern':'+68h]','limit':80})
print('scanned=%s  count=%s' % (r.get('scanned_funcs'), r.get('count')))
print()
for it in (r.get('items') or []):
    print('函数 %s  size=%s  (命中 %d 处)' % (it['func'], it['size'], len(it['hits'])))
    for h in it['hits'][:6]:
        print('      %s  %s' % (h['ea'], h['d']))
