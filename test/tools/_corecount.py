import os, re
ROOT = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'
ORIG = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
keys = ['core_countries', 'should_initiate_resistance', 'is_core_of', 'impassable']
print('=== mod 里出现这些关键词的位置 ===')
for dp, dn, fn in os.walk(ROOT):
    if any(x in dp for x in ['localisation','gfx','sound','portraits','music']): continue
    for f in fn:
        if not f.endswith(('.txt','.lua')): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for k in keys:
            for m in re.finditer(re.escape(k), t):
                ln = t[:m.start()].count(chr(10)) + 1
                line = t.splitlines()[ln-1].strip()[:100] if ln-1 < len(t.splitlines()) else ''
                print('  %-22s %s:%d  %s' % (k, p.replace(ROOT,''), ln, line))
print()
print('=== mod 是否覆盖了同名文件 00_resistance_initiate_triggers.txt ===')
hit = False
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if 'resistance_initiate' in f: print('  ' + os.path.join(dp,f).replace(ROOT,'')); hit = True
if not hit: print('  否 (mod 没有覆盖)')
print()
print('=== 原版里这些关键词还有谁定义 ===')
for dp, dn, fn in os.walk(ORIG + '/common'):
    for f in fn:
        if not f.endswith('.txt'): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for k in ['core_countries']:
            for m in re.finditer(re.escape(k), t):
                ln = t[:m.start()].count(chr(10)) + 1
                line = t.splitlines()[ln-1].strip()[:100] if ln-1 < len(t.splitlines()) else ''
                print('  %s:%d  %s' % (p.replace(ORIG,''), ln, line))
