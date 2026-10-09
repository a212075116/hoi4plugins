import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
print('=== CLexer 虚表 (0x142B912F0) ===')
for i in range(20):
    r = send({'op':'bytes','ea':hex(0x142B912F0 + i*8),'n':8})
    h = r.get('hex')
    if not h: break
    p = int.from_bytes(bytes.fromhex(h), 'little')
    if p == 0 or not (IMG <= p < 0x14377E000):
        print('   [%d] +0x%02X  %#x (非函数, 停)' % (i, i*8, p)); break
    f = send({'op':'func','ea':hex(p)})
    print('   [%d] +0x%02X  %#010x  %-22s size=%s' % (i, i*8, p-IMG, f.get('name'), f.get('size')))
