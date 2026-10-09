import os, re
ROOT = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'
pats = ['cancel_resistance', 'start_resistance', 'set_resistance', 'add_resistance',
        'set_compliance', 'add_compliance', 'has_resistance', 'set_resistance_target',
        'resistance_target', 'compliance']
hits = {p: [] for p in pats}
nfile = 0
for dp, dn, fn in os.walk(ROOT):
    if 'localisation' in dp or 'gfx' in dp or 'sound' in dp or 'portraits' in dp or 'music' in dp: continue
    for f in fn:
        if not f.endswith(('.txt', '.lua', '.csv')): continue
        p = os.path.join(dp, f)
        nfile += 1
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for pat in pats:
            if pat in t:
                for m in re.finditer(re.escape(pat), t):
                    line = t[:m.start()].count(chr(10)) + 1
                    hits[pat].append((p.replace(ROOT, ''), line))
print('扫描 %d 个文件' % nfile)
for pat in pats:
    h = hits[pat]
    if not h:
        print('  %-22s 0 处' % pat); continue
    print('  %-22s %d 处, 分布在 %d 个文件' % (pat, len(h), len(set(x[0] for x in h))))
print()
print('=== cancel_resistance 出现位置 ===')
for f, l in hits['cancel_resistance']: print('  %s:%d' % (f, l))
print()
print('=== set_resistance / add_resistance / start_resistance ===')
for pat in ['set_resistance', 'add_resistance', 'start_resistance']:
    for f, l in hits[pat]: print('  %-18s %s:%d' % (pat, f, l))
print()
print('=== set_compliance / add_compliance ===')
for pat in ['set_compliance', 'add_compliance']:
    for f, l in hits[pat]: print('  %-18s %s:%d' % (pat, f, l))
