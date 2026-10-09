import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
vt = d['vt']
print('=== CUnitNamesDatabase 相关 ===')
for e in vt:
    c = e.get('cls') or ''
    if 'UnitNames' in c or 'NameDatabase' in c:
        print('    %-60s rva=%#x n=%s' % (c, e.get('rva', 0), e.get('n')))
print('')
print('=== 含 GenerateName 的(RTTI 里 lambda 的签名会带出来) ===')
for e in vt:
    c = e.get('cls') or ''
    if 'GenerateName' in c:
        print('    %s' % c)