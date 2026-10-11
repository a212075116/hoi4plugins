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

for pat in ['add_to_variable', 'subtract_variable', 'multiply_variable', 'divide_variable',
            'modulo_variable', 'round_variable', 'clamp_variable', 'set_variable']:
    r = send({'op': 'strings', 'pattern': pat, 'limit': 12})
    items = r.get('items') or r.get('strings') or []
    print('--- %s : %d' % (pat, len(items)))
    for it in items[:10]:
        if isinstance(it, dict):
            print('   ', it.get('ea'), repr(it.get('text'))[:90])
        else:
            print('   ', it)
