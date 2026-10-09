import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
A = ['CCountry','CState','CProvince','CCharacter','CFleet','CDecision','CEvent','CGameDate','CGameState']
print('== A 组各类的虚表 ==')
for k in A:
    hits = [v for v in d['vt'] if str(v.get('cls','')) == k]
    print('%-12s %d 个虚表' % (k, len(hits)))
    for h in hits:
        print('      rva=%#010x  n=%-3s' % (h.get('rva',0), h.get('n')))