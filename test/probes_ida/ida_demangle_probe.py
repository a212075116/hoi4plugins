# -*- coding: utf-8 -*-
# 探查 IDA demangle 对 vftable 符号的输出格式
import os, json, traceback
import ida_pro, ida_auto, ida_name

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    n = ida_name.get_nlist_size()
    syms = []
    for i in range(n):
        nm = ida_name.get_nlist_name(i)
        if nm and nm.startswith('??_7'):
            syms.append(nm)
    w('total vftable syms=%d' % len(syms))
    fl = 0
    shown = 0
    multi = 0
    for s in syms:
        try:
            d = ida_name.demangle_name(s, ida_name.MNG_SHORT_FORM)
        except Exception:
            d = None
        if not d:
            fl += 1
            if fl <= 10:
                w('FAIL  %s' % s)
        else:
            if 'const' in d[:8] or 'volatile' in d[:11]:
                multi += 1
            if shown < 45:
                w('OK    %-70s => %s' % (s[:70], d))
                shown += 1
    w('\ndemangle_failed=%d  with_cv_prefix=%d' % (fl, multi))
    w('\n--- MNG_LONG_FORM on 5 samples ---')
    for s in syms[:5]:
        try:
            w('  %-70s => %s' % (s[:70], ida_name.demangle_name(s, ida_name.MNG_LONG_FORM)))
        except Exception as e:
            w('  %s => EXC %s' % (s[:70], e))
    w('\n--- multi-inheritance style lookups ---')
    cnt = 0
    for s in syms:
        try:
            d = ida_name.demangle_name(s, ida_name.MNG_SHORT_FORM) or ''
        except Exception:
            continue
        if '{for' in d or 'for `' in d:
            w('  %-70s => %s' % (s[:70], d)); cnt += 1
            if cnt >= 12: break
    w('multi_inheritance_shown=%d' % cnt)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)