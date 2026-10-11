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

# 1) xrefs of the var-text handler
r = send({'op': 'xrefs_to', 'ea': 0x1412CF2B0})
print('=== xrefs_to 0x1412CF2B0 ===')
print(json.dumps(r, ensure_ascii=False)[:1500])
