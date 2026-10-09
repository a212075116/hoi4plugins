# -*- coding: utf-8 -*-
# 从已有数据生成 C++ 头文件骨架（小样演示）
import json, re, sys, collections

V = json.load(open('reports/vt_list.json', encoding='utf-8'))
S = json.load(open('reports/vfunc_sig_full.json', encoding='utf-8'))

# 继承关系：从 类继承层次.md 解析 'Cls : Base1, Base2'
inherit = {}
try:
    txt = open('reports/类继承层次.md', encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'^\s*([A-Za-z_?$][\w@?$:<>,\* ]*?)\s*:\s*(.+)$', txt, re.M):
        k = m.group(1).strip()
        if not k or len(k) > 120: continue
        bases = [b.strip() for b in m.group(2).split(',') if b.strip()]
        inherit.setdefault(k, bases)
except Exception as e:
    print('解析继承失败:', e)
print('继承条目 =', len(inherit))

sigmap = {}
for e in S:
    for fn in e['funcs']:
        if fn['ea'] and fn['sig']:
            sigmap.setdefault(fn['ea'], fn['sig'])

# 找几个有代表性的类
WANT = ['CUnit', 'CProvince', 'CCountry', 'CState', 'CEffect', 'CTrigger', 'CCharacter']
sel = [x for x in V['vt'] if x['cls'] in WANT]
print('选中虚表 =', len(sel))
print('')

out = []
out.append('// HOI4 类骨架（自动生成，来源：RTTI + vftable 恢复）')
out.append('// 生成脚本: flirt/gen_header.py')
out.append('#pragma once')
out.append('')
for x in sel:
    cls = x['cls']
    bases = inherit.get(cls, [])
    out.append('// vftable RVA 0x%X  槽位 %d' % (x['rva'], x['n']))
    if bases:
        bl = ' : public ' + ', public '.join(bases)
    else:
        bl = ''
    out.append('class %s%s {' % (cls, bl))
    out.append('public:')
    simple = re.sub(r'[^A-Za-z0-9_]', '_', cls)
    for k, fn in enumerate(x['funcs'] if 'funcs' in x else []):
        pass
    # 从 vfunc_sig_full 里取该虚表的槽位
    ent = None
    for e in S:
        if e['rva'] == x['rva']:
            ent = e; break
    if ent:
        for fn in ent['funcs']:
            nm = fn['name'] or ('vfunc_%d' % fn['slot'])
            sig = fn['sig'] or ''
            # 从 C 签名提取返回类型与参数
            mm = re.match(r'^(.*?)\s*__fastcall\s*\((.*)\)$', sig) if sig else None
            if mm:
                ret = mm.group(1).strip() or 'void'
                args = mm.group(2).strip() or 'void'
                out.append('    virtual %-28s %-32s // [%2d] 0x%X' % (ret, nm + '(' + args + ');', fn['slot'], fn['ea']))
            else:
                out.append('    virtual void %-36s // [%2d] 0x%X' % (nm + '();', fn['slot'], fn['ea']))
    else:
        out.append('    // 无签名数据')
    out.append('};')
    out.append('')

txt = '\n'.join(out)
open('reports/skeleton_demo.h', 'w', encoding='utf-8').write(txt)
print(txt[:3000])
