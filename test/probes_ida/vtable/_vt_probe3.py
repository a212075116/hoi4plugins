import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send

def q(ea):
    b = send({'op':'bytes','ea':hex(ea),'n':8})
    h = b.get('hex')
    return int.from_bytes(bytes.fromhex(h),'little') if h else None

print('=== 用 0x142969118 做锚点找虚表起点 ===')
slot = 0x142969118
found = False
for back in range(0, 80):
    base = slot - back*8
    col = q(base - 8)
    if col is None or col == 0:
        continue
    sig = q(col)
    if sig != 1:
        continue
    ptd = q(col + 0x0C)
    if ptd is None or ptd == 0:
        continue
    s = send({'op':'read_str','ea':hex(ptd + 0x10),'n':120})
    name = s.get('s') if s.get('ok') else None
    if name:
        print('  虚表起点 = %#x  (倒退 %d 个槽)' % (base, back))
        print('    COL = %#x  sig=%d' % (col, sig))
        print('    类名 = %s' % name)
        found = True
        break
if not found:
    print('  未按 COL 判据找到起点')
print()
print('=== 直接查 0x142969118 附近的符号名 ===')
for ea in [0x142969118 - 8, 0x142969118, 0x142969118 - 0x130, 0x142969118 - 0x138]:
    r = send({'op':'names','needle':'%X' % ea, 'limit':3})
    print('  %#x ->' % ea, [i['name'] for i in (r.get('items') or [])])
