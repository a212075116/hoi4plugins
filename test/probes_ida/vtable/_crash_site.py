import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
IMG = 0x140000000
CRASH = IMG + 0x24B63D3
print('崩溃地址 RVA = 0x24B63D3  绝对 = %#x' % CRASH)
f = send({'op':'func','ea':hex(CRASH)})
print('所在函数: %s  起始=%s  size=%s' % (f.get('name'), f.get('start'), f.get('size')))
print()
print('=== 崩溃点前后反汇编 ===')
d = send({'op':'disasm','ea':hex(CRASH),'count':14,'back':12})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
print()
print('=== 该函数反编译 (前 70 行) ===')
start = f.get('start')
if start:
    r = send({'op':'decompile','ea':start,'lines':70})
    print(r.get('text'))
