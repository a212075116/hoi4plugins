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

r = send({'op': 'decompile', 'ea': 0x1412CF2B0, 'lines': 900})
lines = r.get('text','').split('\n')
print('total', len(lines))
for i, ln in enumerate(lines):
    if 'n9' in ln or 'sub_140535110' in ln or 'sub_14053A610' in ln or '&v166' in ln:
        print('%4d| %s' % (i, ln.strip()[:170]))
