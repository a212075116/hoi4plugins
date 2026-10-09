import os, re
SD = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/history/states'
found = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    try: t = open(p, encoding='utf-8-sig', errors='replace').read()
    except Exception: continue
    if not re.search(r'^\s*controller\s*=', t, re.M): continue
    print('=== ' + fn + ' ===')
    for i, l in enumerate(t.splitlines()[:40]):
        print('  %3d: %s' % (i+1, l))
    found += 1
    if found >= 3: break
print()
print('(原版共 61 个 state 写了 controller)')
