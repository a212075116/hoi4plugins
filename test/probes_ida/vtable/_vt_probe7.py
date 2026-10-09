import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000

def bytes_at(ea, n):
    b = send({'op':'bytes','ea':hex(ea),'n':n})
    return bytes.fromhex(b.get('hex')) if b.get('hex') else None
def u32(ea):
    d = bytes_at(ea, 4)
    return int.from_bytes(d,'little') if d else None
def q64(ea):
    d = bytes_at(ea, 8)
    return int.from_bytes(d,'little') if d else None
def cls_of_vt(vt):
    col = q64(vt - 8)
    if not col: return None
    if u32(col) != 1: return None
    ptd = IMG + u32(col + 0x0C)
    s = send({'op':'read_str','ea':hex(ptd + 0x10),'n':200})
    return s.get('s') if s.get('ok') else None

print('=== sub_140DC53B0 出现在哪些虚表里 ===')
for ref in [0x142969118, 0x142969120]:
    # 往前找虚表起点: VT-8 的 signature==1
    for back in range(0, 200):
        base = ref - back*8
        col = q64(base - 8)
        if not col: continue
        if u32(col) != 1: continue
        ptd = IMG + u32(col + 0x0C)
        s = send({'op':'read_str','ea':hex(ptd + 0x10),'n':200})
        nm = s.get('s') if s.get('ok') else None
        if nm and nm.startswith('.?AV'):
            print('  槽 %#x -> 虚表 %#x  (槽偏移 +0x%X)  类 = %s' % (ref, base, ref-base, nm))
            break
print()
print('=== 检查 0x332F698 / 0x332F260 两个全局槽的 xref ===')
for rva, label in [(0x332F698,'cam slot 0x332F698'), (0x332F260,'CGameState 0x332F260')]:
    x = send({'op':'xrefs_to','ea':hex(IMG + rva)})
    print('  %s: %d 处引用' % (label, x.get('count')))
    for rf in (x.get('refs') or [])[:8]:
        print('     %s in %s' % (rf['from'], rf['func']))
