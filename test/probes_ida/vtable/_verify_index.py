import json, io
from collections import defaultdict
d = json.load(io.open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/sources/1.19.3/vt_index_1.19.3.json', encoding='utf-8'))
vt = d['vt']
byname = defaultdict(list)
for v in vt:
    if v['cls']: byname[v['cls']].append(v)

print('=== 1) CInGameIdler 的全部虚表 ===')
for v in byname.get('CInGameIdler', []):
    print('  sym=%s  rva=%#010x  n=%d  nbase=%s' % (v['sym'], v['rva'], v['n'], v['nbase']))
    for i, s in enumerate(v['slots']):
        if s == 0x00dc53b0:
            print('      >>> 含 sub_140DC53B0 于槽[%d] = +0x%03X' % (i, i*8))
print()
print('=== 2) 同名类最多的 (前 12) ===')
for name, lst in sorted(byname.items(), key=lambda x: -len(x[1]))[:12]:
    print('  %-46s %d 个虚表' % (name[:46], len(lst)))
print()
print('=== 3) 关键游戏类 ===')
for name in ['CInGameIdler','CFrontEndIdler','CGameState','CCurrentGameState','CCountry','CState','CProvince',
             'CCharacter','CArmy','CUnit','CTaskForce','CFleet','CShip','CDecision','CEffect','CTrigger',
             'CGameApplication','CGameDate']:
    lst = byname.get(name)
    if lst:
        print('  %-22s %d 个虚表:' % (name, len(lst)))
        for v in lst[:3]:
            print('      rva=%#010x n=%2d nbase=%s' % (v['rva'], v['n'], v['nbase']))
    else:
        print('  %-22s (无)' % name)
print()
print('=== 4) 名字含 Console/Camera/Cmd 的类 ===')
for v in vt:
    c = v['cls'] or ''
    if any(k in c for k in ('Console','Camera','Cmd')):
        print('  %-46s rva=%#010x n=%2d' % (c[:46], v['rva'], v['n']))
    if len([1 for x in vt if any(k in (x['cls'] or '') for k in ('Console','Camera','Cmd'))]) > 60: break
