import re, os
for n in ('autosave.hoi4', 'VANILLA_1.hoi4', 'TEST_FAIL_AFG_joined_a_faction_500_1_3.hoi4'):
    p = os.path.join(r'C:\\Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games', n)
    b = open(p, 'rb').read()
    print('=== %s (%d 字节) ===' % (n, len(b)))
    print('  头: %r' % b[:12])
    vers = set()
    for m in re.finditer(rb'1\.\d+\.\d+\.\d+[a-z0-9.]*', b):
        vers.add(m.group().decode('ascii', 'replace'))
        if len(vers) > 12: break
    print('  版本串: %s' % sorted(vers)[:12])
    # meta 通常在末尾或开头, 找 game_version / version
    for kw in (b'version', b'game_version', b'savegame_version'):
        i = b.find(kw)
        if i >= 0:
            seg = b[max(0,i-40):i+120]
            print('  %r @%#x -> %r' % (kw, i, seg))
            break
    print('')