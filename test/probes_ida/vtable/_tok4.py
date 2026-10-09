import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
def dump(ea, n, label):
    print('=== %s @ %#x ===' % (label, ea))
    for i in range(n):
        r = send({'op':'bytes','ea':hex(ea + i*8),'n':8})
        h = r.get('hex')
        if not h: break
        p = int.from_bytes(bytes.fromhex(h), 'little')
        note = ''
        if IMG <= p < 0x14377E000:
            f = send({'op':'func','ea':hex(p)})
            nm = f.get('name') or '?'
            note = '  -> %s' % nm
        print('   +%#06x  %#018x%s' % (i*8, p, note))
    print()
dump(0x1427155e8 - 5*8, 16, '引用点1 附近 (0x1427155E8)')
dump(0x1435f9e74 - 4*8, 12, '引用点2 附近 (0x1435F9E74)')
