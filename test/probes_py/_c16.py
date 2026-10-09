import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x140552390','lines':120})
t = r.get('text') if r.get('ok') else ''
print('=== sub_140552390 (命令执行入口) ===')
print(chr(10).join(t.split(chr(10))[:110]))
