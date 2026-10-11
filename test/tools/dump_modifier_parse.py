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

for name, ea in [('sub_1422479F0 modifier-parse', 0x1422479F0), ('sub_140535110 fmt-ctor', 0x140535110)]:
    r = send({'op': 'decompile', 'ea': ea, 'lines': 120})
    print('=' * 20, name, hex(ea), '=' * 20)
    print(r.get('text', r.get('error',''))[:4500])
