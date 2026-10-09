import json, re, collections

V = json.load(open('reports/vt_list.json', encoding='utf-8'))
S = json.load(open('reports/vfunc_sig_full.json', encoding='utf-8'))

cls_vt = collections.defaultdict(list)
for x in V['vt']:
    cls_vt[x['cls']].append(x)
print('classes with vtable =', len(cls_vt))

inherit = {}
children = collections.defaultdict(set)
txt = open('reports/类继承层次.md', encoding='utf-8', errors='replace').read()
np = 0
for m in re.finditer(r'^\s*([A-Za-z_][\w@]*)\s*:\s*(.+)$', txt, re.M):
    k = m.group(1).strip()
    bases = [b.strip() for b in m.group(2).split(',') if b.strip()]
    if k in inherit:
        continue
    inherit[k] = bases
    np += 1
    for b in bases:
        children[b].add(k)
print('inherit parsed =', np)

sig_by_rva = {}
for e in S:
    sig_by_rva[e['rva']] = e['funcs']

FILL = {0x14012A2C0, 0x140120540, 0x14253C3B8, 0x14011D220, 0x140129780, 0x1401807B0}

def stats(cls):
    vts = cls_vt.get(cls, [])
    slots = 0
    uniq = set()
    known = 0
    for v in vts:
        slots += v['n']
        for fn in sig_by_rva.get(v['rva'], []):
            if fn['ea']:
                uniq.add(fn['ea'])
                if fn['sig'] and 'fastcall(__int64)' not in fn['sig']:
                    known += 1
    real = [a for a in uniq if a not in FILL]
    return len(vts), slots, len(uniq), len(real), known

CAND = ['CGameState','CCountry','CState','CProvince','CUnit','CArmy','CFleet','CCharacter',
        'CEffect','CTrigger','CDecision','CEvent','CDatabaseObject','CPersistent',
        'CProfiledScopeObject','CModifier','CGui','CGameDate','CDefineRegistryHelperBase']
print('')
hdr = '%-26s %4s %6s %6s %6s %6s %6s %8s' % ('class','vt','slots','uniq','real','known','bases','children')
print(hdr)
print('-' * len(hdr))
for c in CAND:
    nvt, slots, uniq, real, known = stats(c)
    print('%-26s %4d %6d %6d %6d %6d %6d %8d' % (c, nvt, slots, uniq, real, known,
          len(inherit.get(c, [])), len(children.get(c, set()))))

print('')
print('=== 派生类最多的 20 个基类（结构重要性）===')
for b, ch in sorted(children.items(), key=lambda kv: -len(kv[1]))[:20]:
    print('  %-40s %5d 派生类   自身虚表数=%d' % (b[:40], len(ch), len(cls_vt.get(b, []))))
