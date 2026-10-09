import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
def fullvt(ea, label, n=30):
    print('=== %s @ %#x ===' % (label, ea))
    for i in range(n):
        r = send({'op':'bytes','ea':hex(ea + i*8),'n':8})
        h = r.get('hex')
        if not h: break
        p = int.from_bytes(bytes.fromhex(h), 'little')
        if p == 0: print('   [%2d] +0x%02X  (null) 停止' % (i, i*8)); break
        if not (IMG <= p < 0x14377E000):
            print('   [%2d] +0x%02X  %#x 不在镜像内, 停止' % (i, i*8, p)); break
        f = send({'op':'func','ea':hex(p)})
        nm = f.get('name') or '?'; sz = f.get('size')
        mark = '  <== +0xA8' if i*8 == 0xA8 else ''
        print('   [%2d] +0x%03X  %#010x  %-22s size=%s%s' % (i, i*8, p - IMG, nm, sz, mark))
    print()
fullvt(0x14276edf8, 'CAddStabilityEffect vftable (完整)')
