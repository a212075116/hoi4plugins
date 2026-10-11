# -*- coding: utf-8 -*-
import json, socket, re
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

r = send({'op': 'decompile', 'ea': 0x140542280, 'lines': 90})
print('=== sub_140542280 (variable lookup) ===')
print(r.get('text', r.get('error',''))[:3000])
