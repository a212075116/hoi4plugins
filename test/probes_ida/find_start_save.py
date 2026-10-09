import re
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
b = open(p, 'rb').read()
for kw in (b'start_save', b'start_tag', b'continuelastsave', b'allowoldsave', b'allowoldsaves', b'-start_save', b'start_save='):
    idxs = [m.start() for m in re.finditer(re.escape(kw), b)]
    print('%-22r x%d  %s' % (kw, len(idxs), [hex(i) for i in idxs[:8]]))
print('')
for i in [m.start() for m in re.finditer(re.escape(b'start_save'), b)][:4]:
    s = max(0, i - 300); e = min(len(b), i + 300)
    print('=== start_save @%#x 上下文 ===' % i)
    for m in re.finditer(rb'[ -~]{5,}', b[s:e]):
        print('   %+#x %r' % (m.start() + s, m.group()[:140]))
    print('')