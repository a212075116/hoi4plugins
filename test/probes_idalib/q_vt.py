import json
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json'
d = json.load(open(p, encoding='utf-8'))
target = 0x2935BB8
hits = [v for v in d['vt'] if v.get('rva') == target]
print('目标 rva = %#x' % target)
if hits:
    for h in hits:
        print('  cls=%s' % h.get('cls'))
        print('  sym=%s' % h.get('sym'))
        print('  n=%s' % h.get('n'))
else:
    print('  未命中, 列出附近的:')
    near = sorted(d['vt'], key=lambda v: abs(v.get('rva', 0) - target))[:6]
    for v in near:
        print('    rva=%#x  cls=%s  n=%s' % (v.get('rva', 0), v.get('cls'), v.get('n')))