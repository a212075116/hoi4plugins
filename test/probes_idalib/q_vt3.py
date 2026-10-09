import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
byrva = {}
for v in d['vt']:
    byrva[str(v.get('rva'))] = v
for r in [0x295d8d8, 0x2716590, 0xca6100, 0x2971b18, 0x295d348, 0x27e7360]:
    v = byrva.get(str(r))
    if v:
        print('%#x  n=%-3s  cls=%-40s sym=%s' % (r, v.get('n'), str(v.get('cls'))[:40], str(v.get('sym'))[:90]))
    else:
        print('%#x  (不在 vt_list 里)' % r)