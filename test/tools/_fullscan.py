import os, re
keys = ['should_initiate_resistance']
def scan(root, label):
    print('=== ' + label + ' ===')
    found = []
    for dp, dn, fn in os.walk(root):
        low = dp.lower()
        if any(x in low for x in ['localisation','gfx\\','sound','music','portraits','\\.git']): continue
        for f in fn:
            if not f.endswith('.txt'): continue
            p = os.path.join(dp, f)
            try: t = open(p, encoding='utf-8-sig', errors='replace').read()
            except Exception: continue
            if 'should_initiate_resistance' in t:
                for m in re.finditer(r'should_initiate_resistance', t):
                    ln = t[:m.start()].count(chr(10)) + 1
                    line = t.splitlines()[ln-1].strip()[:95] if ln-1 < len(t.splitlines()) else ''
                    found.append('  %s:%d  %s' % (p.replace(root,''), ln, line))
    if found:
        for x in found[:40]: print(x)
        print('  共 %d 处' % len(found))
    else:
        print('  (无)')
    print()
scan(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa', 'MOD')
scan(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/dlc', 'DLC')
scan(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common', '游戏自带 common')
