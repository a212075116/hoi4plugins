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

def rstr(ea):
    r = send({'op': 'read_str', 'ea': ea, 'size': 120})
    return r.get('text') or r.get('str') or str(r)[:120]

def dump(ea, size, label):
    r = send({'op': 'bytes', 'ea': ea, 'size': size})
    b = bytes.fromhex(r.get('hex',''))
    print('--- %s @%s ---' % (label, hex(ea)))
    for i in range(0, len(b), 8):
        v = struct.unpack_from('<Q', b, i)[0]
        s = ''
        if 0x140000000 <= v <= 0x150000000:
            s = ' code'
        elif 0x142000000 <= v <= 0x148000000:
            s = ' data'
        print('  +0x%02X  %016X%s' % (i, v, s))
    print()

dump(0x142BE1448, 0x60, 'clamp_variable +0x10 data')
dump(0x142BE1148, 0x60, 'set_variable +0x10 data')
