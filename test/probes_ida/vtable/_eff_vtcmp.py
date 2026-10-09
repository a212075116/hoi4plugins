import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
IMG = 0x140000000
def readvt(ea, n=28):
    out = []
    for i in range(n):
        r = send({'op':'bytes','ea':hex(ea + i*8),'n':8})
        h = r.get('hex')
        if not h: break
        p = int.from_bytes(bytes.fromhex(h), 'little')
        if p == 0 or not (IMG <= p < 0x14377E000): break
        out.append(p)
    return out
base = readvt(0x14273D140)
sub  = readvt(0x14276EDF8)
print('CValueEffect      槽数 %d' % len(base))
print('CAddStabilityEffect 槽数 %d' % len(sub))
print()
print('%-6s %-14s %-14s %s' % ('槽', 'CValueEffect', 'CAddStability', '差异'))
for i in range(max(len(base), len(sub))):
    b = base[i] if i < len(base) else None
    s = sub[i] if i < len(sub) else None
    bf = send({'op':'func','ea':hex(b)}) if b else {}
    sf = send({'op':'func','ea':hex(s)}) if s else {}
    bn = bf.get('name') or '?' if b else '(无)'
    sn = sf.get('name') or '?' if s else '(无)'
    bs = bf.get('size') if b else None
    ss = sf.get('size') if s else None
    mark = ''
    if b and s and b != s: mark = '  <== 重写'
    if b and s and b == s: mark = '  (继承)'
    if not b: mark = '  <== 子类新增'
    print('%-6d %-14s %-14s%s' % (i, str(bn)[:14], str(sn)[:14], mark))
    print('       %-14s %-14s  size %s / %s' % ('', '', bs, ss))
