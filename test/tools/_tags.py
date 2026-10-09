import re
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/country_tags/00_countries.txt'
lines = open(p, encoding='utf-8-sig', errors='replace').read().splitlines()
tags = []
for l in lines:
    m = re.match(r'^\s*([A-Za-z0-9_]{3})\s*=\s*"([^"]+)"', l)
    if m: tags.append((m.group(1), m.group(2)))
print('country_tags 条目数: %d' % len(tags))
print()
print('=== 前 45 个 ===')
for i, (t, f) in enumerate(tags[:45]):
    print('  %3d  %s  -> %s' % (i, t, f))
print()
print('=== 找 ADY / ABY / AB1 / AB 开头的 ===')
for i, (t, f) in enumerate(tags):
    if t.startswith('AB') or t.startswith('ODY') or t.startswith('OD1'):
        print('  %3d  %s  -> %s' % (i, t, f))
