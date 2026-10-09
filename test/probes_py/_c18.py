import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x140261D10','lines':130})
t = r.get('text') if r.get('ok') else ''
print('=== sub_140261D10 (无参命令执行) ===')
print(chr(10).join(t.split(chr(10))[:120]))
