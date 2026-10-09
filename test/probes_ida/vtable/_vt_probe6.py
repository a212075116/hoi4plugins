import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000

def bytes_at(ea, n):
    b = send({'op':'bytes','ea':hex(ea),'n':n})
    return bytes.fromhex(b.get('hex')) if b.get('hex') else None
def u32(ea):
    d = bytes_at(ea, 4)
    return int.from_bytes(d, 'little') if d else None
def q64(ea):
    d = bytes_at(ea, 8)
    return int.from_bytes(d, 'little') if d else None

VT = 0x142968ff0
col = q64(VT - 8)
print('虚表起点        = %#x' % VT)
print('VT-8 (COL)      = %#x' % col)
print()
print('=== COL 正确解析 (4 字节 RVA) ===')
print('  signature        = %d' % u32(col + 0x00))
print('  offset           = %d' % u32(col + 0x04))
print('  cdOffset         = %d' % u32(col + 0x08))
ptd = IMG + u32(col + 0x0C)
pcd = IMG + u32(col + 0x10)
print('  pTypeDescriptor  = %#x' % ptd)
print('  pClassDescriptor = %#x' % pcd)
print()
print('=== TypeDescriptor @ %#x ===' % ptd)
print('  原始 32 字节:', bytes_at(ptd, 32).hex())
s = send({'op':'read_str','ea':hex(ptd + 0x10),'n':160})
print('  类名 = %r' % (s.get('s') if s.get('ok') else '?'))
print()
print('=== ClassHierarchyDescriptor @ %#x ===' % pcd)
print('  signature       = %d' % u32(pcd + 0x00))
print('  attributes      = %d' % u32(pcd + 0x04))
print('  numBaseClasses  = %d' % u32(pcd + 0x08))
bca = IMG + u32(pcd + 0x0C)
print('  pBaseClassArray = %#x' % bca)
print()
print('=== 基类链 ===')
n = u32(pcd + 0x08)
for i in range(min(n, 12)):
    p = IMG + u32(bca + i*4)
    s2 = send({'op':'read_str','ea':hex(p + 0x10),'n':120})
    print('  [%d] %s' % (i, s2.get('s') if s2.get('ok') else '?'))
