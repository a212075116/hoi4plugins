# -*- coding: utf-8 -*-
# Hex-Rays 反编译（修正 tag_remove 所属模块）
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_funcs, ida_nalt, ida_typeinf, ida_hexrays, ida_lines
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    ida_hexrays.init_hexrays_plugin()
    for fea in cfg['funcs']:
        fn = ida_funcs.get_func(fea)
        if not fn:
            continue
        nm = ida_name.get_name(fea) or '<noname>'
        w('##### 0x%X  %s' % (fea, nm))
        cf = ida_hexrays.decompile(fea)
        if not cf:
            w('   反编译失败'); continue
        sv = cf.get_pseudocode()
        n = sv.size()
        w('   伪代码共 %d 行，示前 24 行:' % n)
        for i in range(min(n, 24)):
            w('      ' + ida_lines.tag_remove(sv[i].line))
        w('')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)