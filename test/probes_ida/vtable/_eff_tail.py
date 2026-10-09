import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
START = 0x1400036F0
SIZE  = 67098
END   = START + SIZE
print('函数范围: %#x .. %#x' % (START, END))
print()
print('=== 函数最后的 40 条指令 ===')
d = send({'op':'disasm','ea':hex(END - 200),'count':40,'back':0})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
print()
print('=== 该函数调用的所有目标 (统计) ===')
# 用反汇编扫全文找 call, 采样步长 1 太慢, 用 IDA 的 xrefs 反查更慢,
# 改为: 读函数体字节, 用 IDA 的 disasm 分块扫
calls = {}
ea = START
while ea < END:
    d = send({'op':'disasm','ea':hex(ea),'count':300,'back':0})
    t = d.get('text') or d.get('lines') or ''
    ls = t.split(chr(10)) if isinstance(t,str) else list(t)
    if not ls: break
    last = None
    for l in ls:
        if 'call' in l:
            parts = l.split()
            tgt = parts[-1]
            calls[tgt] = calls.get(tgt, 0) + 1
        last = l
    if last is None: break
    try:
        next_ea = int(last.split()[0], 16)
    except Exception:
        break
    if next_ea <= ea: break
    ea = next_ea
print('  扫描到 %#x' % ea)
for k, v in sorted(calls.items(), key=lambda x: -x[1])[:25]:
    print('    %-34s %d 次' % (k, v))
