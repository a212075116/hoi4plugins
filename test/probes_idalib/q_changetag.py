import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
want = ['CChangeTagEffect', 'CCountryTag', 'CCountryTagAliasEntry', 'CTagTrigger', 'CRandomCountryWithOriginalTag']
for kw in want:
    hits = [v for v in d['vt'] if str(v.get('cls','')) == kw]
    print('== %s : %d 个虚表 ==' % (kw, len(hits)))
    for h in hits:
        print('    rva=%#x  n=%s  sym=%s' % (h.get('rva',0), h.get('n'), str(h.get('sym'))[:80]))