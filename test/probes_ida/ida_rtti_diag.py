# -*- coding: utf-8 -*-
# 只读诊断：数据库里 RTTI / vftable / C++ 名字的恢复程度
import os, json, collections, re
import ida_funcs, ida_pro, ida_auto, ida_name, ida_typeinf, ida_nalt, ida_segment

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
ida_auto.auto_wait()
f.write('func_qty=%d\n' % ida_funcs.get_func_qty())

n = ida_name.get_nlist_size()
f.write('nlist_size=%d\n' % n)
stats = collections.Counter()
samples = collections.defaultdict(list)
for i in range(n):
    nm = ida_name.get_nlist_name(i)
    if not nm:
        continue
    if nm.startswith('??_7'):
        k = 'vftable(??_7)'
    elif nm.startswith('??_R'):
        k = 'RTTI_data(??_R)'
    elif nm.startswith('??_8'):
        k = 'vbtable(??_8)'
    elif nm.startswith('??_C'):
        k = 'string_lit(??_C)'
    elif nm.startswith('??_E') or nm.startswith('??_G'):
        k = 'scalar_deleting_dtor'
    elif '@@' in nm:
        k = 'mangled_cpp_other'
    elif nm.startswith('sub_'):
        k = 'sub_'
    elif nm.startswith('unknown_libname_'):
        k = 'unknown_libname_'
    elif nm.startswith('loc_') or nm.startswith('byte_') or nm.startswith('dword_') or nm.startswith('qword_') or nm.startswith('off_') or nm.startswith('unk_'):
        k = 'auto_loc'
    else:
        k = 'plain_other'
    stats[k] += 1
    if len(samples[k]) < 6:
        samples[k].append(nm)
for k, v in stats.most_common():
    f.write('%-24s %d\n' % (k, v))
f.write('\n--- samples ---\n')
for k in stats:
    f.write('[%s]\n' % k)
    for s in samples[k]:
        f.write('    %s\n' % s)

# local types 里的类数量
til = ida_typeinf.get_idati()
try:
    qty = ida_typeinf.get_ordinal_qty(til)
except Exception as e:
    qty = -1
f.write('\ntype_ordinal_qty=%s\n' % qty)
cls = 0
tinfo = ida_typeinf.tinfo_t()
checked = 0
if qty and qty > 0:
    for o in range(1, min(qty, 200000)):
        if ida_typeinf.get_numbered_type(til, o, tinfo):
            checked += 1
            if tinfo.is_struct() or tinfo.is_udt():
                cls += 1
f.write('checked_types=%d  udt_like=%d\n' % (checked, cls))
f.close()
ida_pro.qexit(0)