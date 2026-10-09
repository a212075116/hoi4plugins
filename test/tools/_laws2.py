def show(p, name, n, tag):
    try:
        ln = open(p, encoding='utf-8-sig', errors='replace').read().splitlines()
    except Exception as e:
        print('%s: 读取失败 %s' % (tag, e)); return
    start = None
    for i, l in enumerate(ln):
        if l.startswith(name + ' ') or l.startswith(name + '=') or l.startswith(name + ' ='):
            start = i; break
        if l.startswith(name + '\t=') or l.startswith(name + '{'):
            pass
    if start is None:
        print('%s: 未找到 %s' % (tag, name)); return
    print('=== %s  %s (行 %d) ===' % (tag, name, start+1))
    for i in range(start, min(start+n, len(ln))):
        print('  %4d: %s' % (i+1, ln[i]))
    print()

show(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/occupation_laws/occupation_laws.txt', 'no_garrison', 26, '原版')
show(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/occupation_laws/occupation_laws.txt', 'missing_garrison_scaled_effect', 30, '原版')
show(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/occupation_laws/occupation_laws.txt', 'missing_garrison_scaled_effect', 30, 'mod')
