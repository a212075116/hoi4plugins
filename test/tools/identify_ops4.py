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

for ea in [0x140360250, 0x14034F750]:
    r = send({'op': 'decompile', 'ea': ea, 'lines': 110})
    print('=' * 20, hex(ea), '=' * 20)
    print(r.get('text', r.get('error',''))[:3200])
    print()

# clamp 候选: 搜变量查找函数调用者里还没认领的
r = send({'op': 'xrefs_to', 'ea': 0x140542280})
claimed = {0x14034C760,0x140366BC0,0x14035B9E0,0x140355C70,0x140364C60,0x140360250,0x14034F750,
           0x140345000,0x140345C30,0x140346A10,0x140347370,0x140350C40}
print('=== unclaimed callers of 0x140542280 ===')
for ref in r.get('refs', []):
    f = ref.get('func')
    if not f: continue
    v = int(f, 16)
    if v not in claimed:
        print('  ', f)
