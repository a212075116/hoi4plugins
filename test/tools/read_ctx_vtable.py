# -*- coding: utf-8 -*-
import json, socket, struct
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

VT = 0x1427DE358
r = send({'op': 'bytes', 'ea': VT, 'size': 0x48})
print('bytes reply keys:', list(r.keys()))
data = r.get('bytes') or r.get('data') or r.get('hex')
print('raw:', str(data)[:400])
