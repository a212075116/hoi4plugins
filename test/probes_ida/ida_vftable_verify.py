# -*- coding: utf-8 -*-
# 只读验证：虚函数命名后的数据库状态
import os, json, collections, traceback
import ida_pro, ida_auto, ida_name, ida_funcs
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    qty = ida_funcs.get_func_qty()
    named = unnamed = 0
    buckets = collections.Counter()
    samples = collections.defaultdict(list)
    for i in range(qty):
        fn = ida_funcs.getn_func(i)
        if fn is None:
            continue
        nm = ida_funcs.get_func_name(fn.start_ea) or ''
        if nm.startswith(('sub_', 'unknown_', 'nullsub_', 'j_sub_')):
            unnamed += 1; k = 'UNNAMED'
        else:
            named += 1
            if '::vfunc_' in nm:
                k = 'Class::vfunc_N'
            elif '::vtbl' in nm:
                k = 'Class::vtblX::vfunc_N'
            elif nm.startswith('??') or nm.startswith('?'):
                k = 'mangled_cpp'
            elif '::' in nm:
                k = 'cpp_qualified'
            else:
                k = 'plain'
        buckets[k] += 1
        if len(samples[k]) < 14:
            samples[k].append(nm)
    w('func_qty=%d  named=%d  unnamed=%d  named_pct=%.1f' % (qty, named, unnamed, 100.0 * named / max(1, qty)))
    for k, v in buckets.most_common():
        w('  %-24s %d' % (k, v))
    for k in ('Class::vfunc_N', 'Class::vtblX::vfunc_N', 'cpp_qualified'):
        w('\n--- sample %s ---' % k)
        for s in samples[k]:
            w('    ' + s[:150])
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)