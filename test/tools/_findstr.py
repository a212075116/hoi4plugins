import re
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
d = open(p, 'rb').read()
print('size=%d' % len(d))
keys = [b'GetOccupationLaw', b'no occupatin data', b'resistance.cpp']
for k in keys:
    idxs = []
    st = 0
    while True:
        i = d.find(k, st)
        if i < 0: break
        idxs.append(i)
        st = i + 1
    print()
    print('%s : %d 处' % (k.decode(), len(idxs)))
    for i in idxs[:6]:
        lo = max(0, i-60); hi = min(len(d), i+120)
        seg = d[lo:hi]
        txt = ''.join(chr(c) if 32 <= c < 127 else '.' for c in seg)
        print('  fileoff=%#x  ...%s...' % (i, txt))
