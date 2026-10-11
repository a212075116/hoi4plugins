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

r = send({'op': 'xrefs_to', 'ea': 0x140542280})
print('=== xrefs_to 0x140542280 (variable lookup) ===')
print('count=', r.get('count'))
seen = {}
for ref in r.get('refs', []):
    fn = ref.get('func')
    seen.setdefault(fn, []).append(ref.get('from'))
for fn, froms in seen.items():
    print('  func=%s  calls=%d  first=%s' % (fn, len(froms), froms[0]))
