import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
for kw in ['CReferenceObject', 'CReference']:
    hits = [v for v in d['vt'] if kw.lower() in str(v.get('cls','')).lower()]
    print('== %s : %d ==' % (kw, len(hits)))
    for h in hits[:15]:
        print('    rva=%#010x n=%-3s cls=%s' % (h.get('rva',0), h.get('n'), h.get('cls')))
    print('')
# 找所有 n 很小且被 CCharacter/CFleet 共用的基类候选
print('== 所有含 Reference 的类 ==')
s = set()
for v in d['vt']:
    c = str(v.get('cls',''))
    if 'Reference' in c: s.add(c)
for c in sorted(s): print('   ', c)