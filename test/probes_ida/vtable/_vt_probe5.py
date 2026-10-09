import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send

def q(ea):
    b = send({'op':'bytes','ea':hex(ea),'n':8})
    h = b.get('hex')
    return int.from_bytes(bytes.fromhex(h),'little') if h else None

VT = 0x142968ff0
print('=== 谁引用了虚表 %#x ===' % VT)
x = send({'op':'xrefs_to','ea':hex(VT)})
print('  引用数 =', x.get('count'))
for rf in (x.get('refs') or [])[:10]:
    print('    %s  in %s' % (rf['from'], rf['func']))
print()
print('=== 用 names 模糊查这个地址 ===')
r = send({'op':'names','needle':'142968FF0','limit':5})
for it in (r.get('items') or []): print('   %s %s' % (it['ea'], it['name']))
r2 = send({'op':'names','needle':'142968ff0','limit':5})
for it in (r2.get('items') or []): print('   %s %s' % (it['ea'], it['name']))
print()
# 虚表前面那个 8 字节(即 VT-8)到底指向什么
col = q(VT - 8)
print('VT-8 = %#x' % col)
if col and 0x140000000 <= col < 0x144000000:
    print('  在 image 内, 读它的 0x20 字节:')
    b = send({'op':'bytes','ea':hex(col),'n':0x20})
    print('   ', b.get('hex'))
    print('   [0x00] sig   = %d' % q(col + 0x00))
    print('   [0x04] offset= %d' % q(col + 0x04))
    print('   [0x08] cd    = %d' % q(col + 0x08))
    print('   [0x10] pTD   = %#x' % q(col + 0x10))
    print('   [0x18] pCD   = %#x' % q(col + 0x18))
