import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send

def q(ea):
    b = send({'op':'bytes','ea':hex(ea),'n':8})
    h = b.get('hex')
    return int.from_bytes(bytes.fromhex(h),'little') if h else None

def rd(ea, n=8):
    b = send({'op':'bytes','ea':hex(ea),'n':n})
    return bytes.fromhex(b.get('hex')) if b.get('hex') else None

col = 0x142cdec08
print('=== COL @ %#x ===' % col)
sig   = q(col + 0x00)
off   = q(col + 0x04)
cd    = q(col + 0x08)
ptd   = q(col + 0x10)
pcd   = q(col + 0x18)
print('  signature      = %d' % sig)
print('  offset         = %d' % off)
print('  cdOffset       = %d' % cd)
print('  pTypeDescriptor= %#x' % ptd)
print('  pClassDescriptor=%#x' % pcd)
print()
print('=== TypeDescriptor @ %#x ===' % ptd)
print('  raw 48 字节:', rd(ptd, 48).hex() if rd(ptd,48) else '?')
s = send({'op':'read_str','ea':hex(ptd + 0x10),'n':160})
print('  name @ +0x10 = %r' % (s.get('s') if s.get('ok') else '?'))
print()
print('=== ClassHierarchyDescriptor @ %#x ===' % pcd)
print('  signature       = %d' % q(pcd + 0x00))
print('  attributes      = %d' % q(pcd + 0x04))
print('  numBaseClasses  = %d' % q(pcd + 0x08))
print('  pBaseClassArray = %#x' % q(pcd + 0x10))
print()
print('=== 虚表起点 0x142968ff0 的前 5 个槽 ===')
for i in range(5):
    print('  [%d] %#x' % (i, q(0x142968ff0 + i*8)))
