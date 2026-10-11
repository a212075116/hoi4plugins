# -*- coding: utf-8 -*-
import json, socket
def send(obj):
    s = socket.create_connection(('127.0.0.1', 19531), timeout=300)
    s.sendall((json.dumps(obj) + '\n').encode('utf-8'))
    buf = b''
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
        try: return json.loads(buf.decode('utf-8'))
        except Exception: continue
    return json.loads(buf.decode('utf-8'))

cands = [0x140345000, 0x140345C30, 0x140346A10, 0x140347370, 0x14034C760,
         0x14034F750, 0x140350C40, 0x140355C70, 0x14035B9E0, 0x140360250, 0x140366BC0]
for ea in cands:
    r = send({'op': 'disasm', 'ea': ea, 'count': 40})
    txt = r.get('text') or r.get('lines') or ''
    if isinstance(txt, list):
        txt = '\n'.join(str(x) for x in txt)
    ops = []
    for ln in str(txt).split('\n'):
        low = ln.lower()
        if any(k in low for k in ['imul', 'idiv', 'add ', 'sub ', 'mul', 'div', 'and ', 'or ']):
            ops.append(ln.strip()[:100])
    print('=== %s ===' % hex(ea))
    for o in ops[:8]:
        print('   ', o)
