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

def dump(base_ea, size, label):
    r = send({'op': 'bytes', 'ea': base_ea, 'size': size})
    b = bytes.fromhex(r.get('hex',''))
    print('--- %s  @%s  (%d bytes) ---' % (label, hex(base_ea), len(b)))
    for i in range(0, len(b), 8):
        v = struct.unpack_from('<Q', b, i)[0]
        tag = ''
        if 0x140000000 <= v <= 0x150000000: tag = ' <code>'
        elif 0x142000000 <= v <= 0x143000000: tag = ' <data>'
        print('  +0x%02X  %016X%s' % (i, v, tag))
    print()

dump(0x14277C638, 0x40, 'clamp_temp_variable entryVt')
dump(0x14277C680, 0x40, 'clamp_variable entryVt')
dump(0x14277C418, 0x20, 'set_variable entryVt (ours)')
dump(0x14277CED8, 0x20, 'STAB_ENTRY_VT (base default)')
