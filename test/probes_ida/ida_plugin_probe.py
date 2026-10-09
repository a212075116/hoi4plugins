# -*- coding: utf-8 -*-
# 探查：已安装的类恢复插件能否被脚本调用
import os, json, traceback
import ida_pro, ida_auto, ida_idaapi, ida_ida, ida_kernwin
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    try:
        w('kernel: %s' % ida_kernwin.get_kernel_version())
    except Exception as e:
        w('kernel: n/a (%s)' % e)
    pl = None
    for mod in ('ida_ida', 'ida_idaapi'):
        m = globals().get(mod)
        if m is not None and hasattr(m, 'get_plugins'):
            pl = m.get_plugins(); break
    names = []
    if pl:
        for p in pl:
            try:
                names.append((getattr(p, 'name', ''), getattr(p, 'file', '')))
            except Exception:
                pass
    w('plugin count=%d' % len(names))
    w('\n--- class/vtable related ---')
    for n, fl in names:
        s = ((n or '') + ' ' + (fl or '')).lower()
        if 'class' in s or 'hrt' in s or 'vtable' in s or 'hexray' in s:
            w('  MATCH  name=%-28s file=%s' % (n, fl))
    w('\n--- all plugin names ---')
    w(', '.join(sorted(set(n for n, _ in names if n))))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)