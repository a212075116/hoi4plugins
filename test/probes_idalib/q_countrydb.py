import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
kws = ['CountryDatabase', 'CountryTagDatabase', 'CountryTag']
for kw in kws:
    hits = [v for v in d['vt'] if kw.lower() in str(v.get('cls','')).lower()]
    print('== %s : %d ==' % (kw, len(hits)))
    for h in hits[:12]:
        print('    rva=%#x n=%-3s cls=%s' % (h.get('rva',0), h.get('n'), str(h.get('cls'))[:60]))
    print('')
# 所有含 Country 的类名(去重)
s = set()
for v in d['vt']:
    c = str(v.get('cls',''))
    if 'Country' in c and 'Trigger' not in c and 'Effect' not in c:
        s.add(c)
print('== 含 Country 的类(前 40) ==')
for c in sorted(s)[:40]:
    print('   ', c)