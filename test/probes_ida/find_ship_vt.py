import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
vt = d['vt']
print('=== 类名精确匹配 CShip / CTaskForce / CNavy / CFleet 系 ===')
import re
pats = ['CShip', 'CTaskForce', 'CTaskforce', 'CNavy', 'CFleet', 'CNaval']
for e in vt:
    c = e.get('cls') or ''
    for p in pats:
        if re.match(r'^' + p + r'(@|$|@@)', c) or c == p:
            print('   %-46s rva=%#x n=%s' % (c, e.get('rva', 0), e.get('n')))
            break
print('')
print('=== 含 Ship 的类(前 40) ===')
n = 0
for e in vt:
    c = e.get('cls') or ''
    if 'Ship' in c and not c.startswith('?'):
        print('   %-46s rva=%#x n=%s' % (c, e.get('rva', 0), e.get('n')))
        n += 1
        if n >= 40: break