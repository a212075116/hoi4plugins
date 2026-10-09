import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
# 直接看 sub_140250340 的反汇编, 确认 IDA 用的偏移写法
r = send({'op':'disasm','ea':'0x140250340','count':30})
print('=== sub_140250340 反汇编 (debug_zoom 处理函数) ===')
for ln in (r.get('lines') or []): print(ln)
print()
r2 = send({'op':'func','ea':'0x140250340'})
print('func:', json.dumps(r2, ensure_ascii=False))
print()
# 试不同写法
for pat in ['6D4h', '+6D4h', '6D4', '1748']:
    rr = send({'op':'grep_disasm','pattern':pat,'limit':8})
    print('grep %-8r -> count=%s' % (pat, rr.get('count')))
    for it in (rr.get('items') or [])[:4]:
        print('      %s (size=%s)  %s' % (it['func'], it['size'], it['hits'][0]['d'] if it['hits'] else ''))
