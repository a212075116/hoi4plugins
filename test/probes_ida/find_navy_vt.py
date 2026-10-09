import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
vt = d['vt']
print('总虚表数:', len(vt))
print('')
print('=== 名字含 Navy 的 ===')
for e in vt:
    if 'Navy' in (e.get('cls') or ''):
        print('    %-40s ea=%#x rva=%#x n=%s' % (e.get('cls'), e.get('ea', 0), e.get('rva', 0), e.get('n')))
print('')
print('=== 名字含 Fleet 的 ===')
for e in vt:
    if 'Fleet' in (e.get('cls') or ''):
        print('    %-40s ea=%#x rva=%#x n=%s' % (e.get('cls'), e.get('ea', 0), e.get('rva', 0), e.get('n')))
print('')
print('=== 名字含 TaskForce / Ship 的 ===')
for e in vt:
    c = e.get('cls') or ''
    if 'TaskForce' in c or 'Taskforce' in c or c.startswith('CShip'):
        print('    %-40s ea=%#x rva=%#x n=%s' % (c, e.get('ea', 0), e.get('rva', 0), e.get('n')))