import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
t0 = time.time()
r = send({'op':'grep_disasm','pattern':'+69Ch','limit':200})
print('scanned=%s  count=%s  用时%.1fs' % (r.get('scanned_funcs'), r.get('count'), time.time()-t0))
print()
tot = 0
for it in (r.get('items') or []):
    for h in it['hits']:
        tot += 1
print('命中总数(每函数最多显示6条): %d' % tot)
print()
for it in (r.get('items') or [])[:40]:
    print('函数 %s (size=%s)' % (it['func'], it['size']))
    for h in it['hits']:
        print('    %-14s %s' % (h['ea'], h['d']))
