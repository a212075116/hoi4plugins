# -*- coding: utf-8 -*-
# 只读：评估已生成 vfunc 名字的可读性
import os, json, collections, traceback
import ida_pro, ida_auto, ida_funcs
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    qty = ida_funcs.get_func_qty()
    total = 0
    clean = 0        # 类名部分 <=40 且不含 (_ 的组合
    ugly = 0
    verylong = 0
    len_hist = collections.Counter()
    ugly_samples = []
    clean_samples = []
    for i in range(qty):
        fn = ida_funcs.getn_func(i)
        if fn is None:
            continue
        nm = ida_funcs.get_func_name(fn.start_ea) or ''
        if '::vfunc_' not in nm:
            continue
        total += 1
        cls = nm.rsplit('::vfunc_', 1)[0]
        L = len(cls)
        if L <= 30:
            len_hist['<=30'] += 1
        elif L <= 60:
            len_hist['31-60'] += 1
        elif L <= 100:
            len_hist['61-100'] += 1
        else:
            len_hist['>100'] += 1
        bad = ('(' in cls) or (')' in cls) or (L > 60)
        if bad:
            ugly += 1
            if len(ugly_samples) < 8:
                ugly_samples.append((L, nm[:150]))
        else:
            clean += 1
            if len(clean_samples) < 10:
                clean_samples.append(nm)
    w('vfunc_named_total=%d  clean=%d (%.1f%%)  ugly=%d (%.1f%%)'
      % (total, clean, 100.0*clean/max(1,total), ugly, 100.0*ugly/max(1,total)))
    w('class-name length histogram: ' + json.dumps(dict(len_hist)))
    w('\n--- clean samples ---')
    for s in clean_samples:
        w('    ' + s)
    w('\n--- ugly samples ---')
    for L, s in ugly_samples:
        w('    [len=%d] %s' % (L, s))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)