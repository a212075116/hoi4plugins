# -*- coding: utf-8 -*-
# 只读抽样：统计已识别函数名前缀分布并取样
import os, json, collections
import ida_funcs, ida_pro, ida_auto

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
ida_auto.auto_wait()
qty = ida_funcs.get_func_qty()
pref = collections.Counter()
samples = collections.defaultdict(list)
def bucket(nm):
    for p in ('boost::', 'std::', '___', '__', 'std_', 'boost_', 'sub_', 'j_', 'nullsub_', 'unknown_', '_'):
        if nm.startswith(p):
            return p
    return 'other'
for i in range(qty):
    fn = ida_funcs.getn_func(i)
    if fn is None:
        continue
    nm = ida_funcs.get_func_name(fn.start_ea) or ''
    b = bucket(nm)
    pref[b] += 1
    if len(samples[b]) < 12:
        samples[b].append(nm)
f.write('func_qty=%d\n' % qty)
for k, v in pref.most_common():
    f.write('%-12s %d\n' % (k, v))
f.write('\n--- samples ---\n')
for k in pref:
    f.write('[%s]\n' % k)
    for s in samples[k]:
        f.write('    %s\n' % s)
f.close()
ida_pro.qexit(0)