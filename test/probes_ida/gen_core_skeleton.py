# -*- coding: utf-8 -*-
# 核心类骨架生成器：信息完整优先，不清洗 mangled 名、不删填充函数
import json, re, collections, os

V = json.load(open('reports/vt_list.json', encoding='utf-8'))
S = json.load(open('reports/vfunc_sig_full.json', encoding='utf-8'))
SIG = {e['rva']: e['funcs'] for e in S}

inherit = {}
children = collections.defaultdict(set)
txt = open('reports/类继承层次.md', encoding='utf-8', errors='replace').read()
for m in re.finditer(r'^\s*([A-Za-z_][\w@]*)\s*:\s*(.+)$', txt, re.M):
    k = m.group(1).strip()
    if k in inherit: continue
    bs = [b.strip() for b in m.group(2).split(',') if b.strip()]
    inherit[k] = bs
    for b in bs: children[b].add(k)

# 填充函数（实测机器码）
FILL = {
    0x14012A2C0: 'ret (empty stub)',
    0x140120540: 'xor eax,eax; ret (returns 0)',
    0x14253C3B8: '_purecall',
    0x14011D220: 'shared filler (CFile::vfunc_10 nom.)',
    0x140129780: 'CRT filler (?GetLocaleT@_LocaleUpdate)',
    0x1401807B0: 'shared filler (CAchievementsContext::vfunc_8 nom.)',
}

# 运行时实例数（来自 frida 归属验证）
RUNTIME = {
    'CTrigger': 74075, 'CEffect': 33405, 'CCharacter': 13913, 'CProvince': 9974,
    'CCountry': 496, 'CState': 446, 'CDecision': 167, 'CUnit': 21, 'CArmy': 21,
    'CGameState': 1,
}

CORE = ['CGameState','CCountry','CState','CProvince','CUnit','CArmy','CFleet',
        'CCharacter','CEffect','CTrigger','CDecision','CEvent','CGui','CGameDate',
        'CDatabaseObject','CPersistent','CProfiledScopeObject']

cls_vt = collections.defaultdict(list)
for x in V['vt']:
    cls_vt[x['cls']].append(x)

out = []
out.append('// =====================================================================')
out.append('// HOI4 核心类骨架  —  自动生成，未做任何名称清洗')
out.append('// 生成: flirt/gen_core_skeleton.py')
out.append('//')
out.append('// 阅读约定:')
out.append('//   [n]        vftable 槽位序号（决定 vtable 布局）')
out.append('//   @0x...     静态地址（imagebase = 0x140000000）')
out.append('//   <FILL>     填充函数：纯虚/空实现，非本类逻辑')
out.append('//   <OTHER>    该地址同时被别的类命名，属共享填充，勿当作本类方法')
out.append('//   mangled 名原样保留，因为它是判断归属与跨类复用的唯一可靠线索')
out.append('// =====================================================================')
out.append('')

for cls in CORE:
    vts = cls_vt.get(cls, [])
    if not vts:
        out.append('// ---- %s : 无虚表（可能是纯数据类或模板基类）----' % cls)
        nch = len(children.get(cls, set()))
        if nch:
            out.append('//      派生类数 = %d' % nch)
        out.append('')
        continue
    bases = inherit.get(cls, [])
    nch = len(children.get(cls, set()))
    rt = RUNTIME.get(cls)
    out.append('// =====================================================================')
    out.append('// class %s' % cls)
    out.append('//   虚表数 = %d   派生类数 = %d   基类数 = %d%s' % (
        len(vts), nch, len(bases), ('   运行时实测量 = %d' % rt) if rt else ''))
    if bases:
        out.append('//   基类(按最多派生优先): %s' % ', '.join(bases))
    out.append('// =====================================================================')
    if bases:
        out.append('class %s : public %s {' % (cls, ', public '.join(bases)))
    else:
        out.append('class %s {' % cls)
    out.append('public:')
    for vi, v in enumerate(vts):
        tag = '' if vi == 0 else '   // 次虚表 #%d（多重继承）' % vi
        out.append('    // --- vftable @0x%X  RVA 0x%X  槽位 %d%s' % (v['ea'], v['rva'], v['n'], tag))
        for fn in SIG.get(v['rva'], [])[:v['n']]:
            ea = fn['ea']
            nm = fn['name'] or ('__slot%d' % fn['slot'])
            sig = fn['sig'] or '<签名未知>'
            mark = ''
            if ea in FILL:
                mark = '   // <FILL> ' + FILL[ea]
            elif nm and '::' in nm and not nm.startswith(cls + '::'):
                base = nm.split('::')[0].lstrip('?')
                mark = '   // <OTHER> 归属 %s（共享填充或基类实现）' % base
            out.append('    virtual %-58s // [%2d] @0x%-10X %s' % (
                (nm + '();')[:58], fn['slot'], ea or 0, mark))
        out.append('')
    out.append('};')
    out.append('')

os.makedirs('reports/skeleton', exist_ok=True)
body = '\n'.join(out)
open('reports/skeleton/core_skeleton.h', 'w', encoding='utf-8').write(body)
print('written reports/skeleton/core_skeleton.h =', len(body), 'bytes')
print('classes =', body.count('\nclass ') + body.count('\n// class '))
print('')
print(body[:2600])
