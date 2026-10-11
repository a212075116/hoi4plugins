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

r = send({'op': 'decompile', 'ea': 0x1412CF2B0, 'lines': 900})
txt = r.get('text', r.get('error',''))
lines = txt.split('\n')
print('TOTAL LINES:', len(lines))
# 关键字过滤: 虚函数调用 / 颜色相关 / 167 / 17
keys = ['(*(', '0xA7', '167', '\x11', 'colour', 'color', 'Colour', 'Color']
for i, ln in enumerate(lines):
    if any(k in ln for k in ['*(_QWORD *)a1', '*(_QWORD *)v8', '*(void (__fastcall **)(__int64))', 'a1 +', 'v8 +']):
        print('%4d| %s' % (i, ln.strip()[:160]))
