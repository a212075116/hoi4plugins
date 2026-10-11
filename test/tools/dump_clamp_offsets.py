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

r = send({'op': 'decompile', 'ea': 0x14034F750, 'lines': 260})
t = r.get('text','')
print('TOTAL LINES', len(t.split('\n')))
for i, ln in enumerate(t.split('\n')):
    s = ln.strip()
    if re.search(r'a1 \+ \d+|sub_140544C90|sub_140545A30|sub_140542280', s):
        print('%4d| %s' % (i, s[:150]))
