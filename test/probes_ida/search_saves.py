import re
for name in ('1.hoi4', 'ABY_500_01_01_01.hoi4', 'autosave.hoi4'):
    p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/' + name
    try:
        b = open(p, 'rb').read()
    except Exception as e:
        print('%s: 打不开 %s' % (name, e)); continue
    print('=== %s  (%d 字节) ===' % (name, len(b)))
    for kw in (b'ABY', b'AB1', b'MIL', b'FLEET', b'fleet', b'task_force'):
        print('   %-12r x%d' % (kw, b.count(kw)))
    print('')