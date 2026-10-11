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

cands = [0x140345000, 0x140345C30, 0x140346A10, 0x140347370, 0x14034F750, 0x140350C40, 0x140360250]
for ea in cands:
    r = send({'op': 'decompile', 'ea': ea, 'lines': 120})
    t = r.get('text', r.get('error',''))
    print('=' * 18, hex(ea), '=' * 18)
    for ln in t.split('\n'):
        s = ln.strip()
        if not s: continue
        if re.search(r'\*v6|\*v[0-9]+\s*[+\-*/%]?=|v[0-9]+ / |v[0-9]+ % |imul|idiv|sub_14053|sub_140542280|sub_140544C90', s):
            print('   ', s[:150])
    print()
