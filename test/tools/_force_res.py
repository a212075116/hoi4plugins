import os, re
ROOT = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'
keys = ['force_enable_resistance', 'start_resistance', 'cancel_resistance',
        'set_resistance', 'add_resistance', 'set_compliance', 'add_compliance',
        'add_resistance_target', 'remove_resistance_target', 'resistance_target']
hits = {k: [] for k in keys}
for dp, dn, fn in os.walk(ROOT):
    if any(x in dp for x in ['localisation','gfx','sound','portraits','music']): continue
    for f in fn:
        if not f.endswith(('.txt','.lua','.csv')): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for k in keys:
            for m in re.finditer(r'\b' + k + r'\b', t):
                ln = t[:m.start()].count(chr(10)) + 1
                hits[k].append((p.replace(ROOT, ''), ln, t.splitlines()[ln-1].strip()[:90] if ln-1 < len(t.splitlines()) else ''))
for k in keys:
    h = hits[k]
    print('%-26s %d 处' % (k, len(h)))
    for f, l, src in h[:14]:
        print('      %s:%d   %s' % (f, l, src))
