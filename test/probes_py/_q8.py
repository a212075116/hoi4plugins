import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
f = send({'op':'func','ea':'0x1400036F0'})
print('sub_1400036F0:', json.dumps(f, ensure_ascii=False))
end = int(f['end'], 16)
print()
print('=== 函数最后 60 条指令 (找注册调用) ===')
r = send({'op':'disasm','ea':hex(end - 0x180),'count':60})
for ln in (r.get('lines') or []): print(ln)
