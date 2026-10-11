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

# set_variable entryVt 已知 0x277C418; 看看这块数据区里有哪些指针(可能是一组 effect entry vtable)
r = send({'op': 'bytes', 'ea': 0x14277C400, 'size': 0x120})
h = r.get('hex', '')
b = bytes.fromhex(h)
print('base 0x14277C400, len', len(b))
vals = []
for i in range(0, len(b) - 7, 8):
    v = struct.unpack_from('<Q', b, i)[0]
    vals.append((0x14277C400 + i, v))
for ea, v in vals:
    tag = ''
    if 0x140000000 <= v <= 0x150000000:
        tag = '  <- code ptr'
    print('%s  %016X%s' % (hex(ea), v, tag))
