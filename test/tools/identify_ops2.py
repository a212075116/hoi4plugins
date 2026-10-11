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

for ea in [0x14034C760, 0x140366BC0, 0x14035B9E0, 0x140355C70]:
    r = send({'op': 'decompile', 'ea': ea, 'lines': 90})
    t = r.get('text', r.get('error',''))
    print('=' * 22, hex(ea), '=' * 22)
    print(t[:2200])
    print()
