# -*- coding: utf-8 -*-
import sys, json, socket
HOST, PORT = '127.0.0.1', 19531
def send(obj):
    s = socket.create_connection((HOST, PORT), timeout=180)
    s.sendall((json.dumps(obj) + '\n').encode('utf-8'))
    buf = b''
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
        try:
            return json.loads(buf.decode('utf-8'))
        except Exception:
            continue
    s.close()
    return json.loads(buf.decode('utf-8'))

r = send({'op': 'decompile', 'ea': 0x140364C60, 'lines': 130})
print('OK=', r.get('ok'))
print(r.get('text', r.get('error', ''))[:6000])
