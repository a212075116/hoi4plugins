import re, os
d = r'C:\\Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games'
for n in ('VANILLA_PATCHED.hoi4', 'TEST_FAIL_AFG_joined_a_faction_500_1_3.hoi4'):
    b = open(os.path.join(d, n), 'rb').read()
    print('=== %s ===' % n)
    for kw in (b'checksum', b'Checksum', b'old', b'mods', b'version'):
        idxs = [m.start() for m in re.finditer(re.escape(kw), b)][:4]
        print('   %-12r x%d %s' % (kw, len(idxs), [hex(i) for i in idxs]))
    print('')