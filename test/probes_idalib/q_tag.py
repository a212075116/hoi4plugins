import json, re
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
vts = d['vt']
print('总虚表数: %d' % len(vts))
for kw in ['CTag', 'Tag', 'CountryTag']:
    hits = [v for v in vts if kw.lower() in str(v.get('cls','')).lower() or kw.lower() in str(v.get('sym','')).lower()]
    print('== 关键词 %s : %d 个 ==' % (kw, len(hits)))
    seen = set()
    for h in hits[:20]:
        c = h.get('cls')
        if c in seen: continue
        seen.add(c)
        print('    rva=%#x  cls=%s  n=%s' % (h.get('rva',0), c, h.get('n')))