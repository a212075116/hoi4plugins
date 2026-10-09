import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
print('=== sub_1400831C0 函数范围 ===')
print(json.dumps(send({'op':'func','ea':'0x1400831C0'}), ensure_ascii=False))
print()
print('=== set_variable 引用点附近 (0x140098900 起 55 条) ===')
r = send({'op':'disasm','ea':'0x140098900','count':55})
for ln in (r.get('lines') or []): print(ln)
print()
print('=== set_variable 字符串引用点附近 (0x1400988f0 起, 含后面 40 条) ===')
r2 = send({'op':'disasm','ea':'0x140098937','count':40,'back':6})
for ln in (r2.get('lines') or []): print(ln)
