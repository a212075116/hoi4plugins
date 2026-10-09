# -*- coding: utf-8 -*-
# 找虚表的所有代码引用（构造函数写虚表指针的地方）
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_nalt, ida_bytes, ida_xref, idautils, ida_funcs
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
TARGETS = cfg['targets']
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    for want in TARGETS:
        ea = ida_name.get_name_ea(ida_nalt.get_imagebase() - ida_nalt.get_imagebase(), want)
        ea = None
        # 遍历名字表找符号
        n = ida_name.get_nlist_size()
        for i in range(n):
            if ida_name.get_nlist_name(i) == want:
                ea = ida_name.get_nlist_ea(i)
                break
        if ea is None:
            w('MISSING %s' % want)
            continue
        drefs = list(idautils.DataRefsTo(ea))
        crefs = list(idautils.CodeRefsTo(ea, 0))
        w('')
        w('##### %s @ 0x%X' % (want, ea))
        w('  data refs = %d   code refs = %d' % (len(drefs), len(crefs)))
        # 数据引用：虚表被嵌入别处；代码引用：构造函数 lea
        for r in drefs[:20]:
            fn = ida_funcs.get_func(r)
            w('    DREF 0x%X  %s  func=%s' % (r, ida_name.get_name(r) or '',
               (ida_name.get_name(fn.start_ea) if fn else '<no func>')))
        for r in crefs[:20]:
            fn = ida_funcs.get_func(r)
            fnm = ida_name.get_name(fn.start_ea) if fn else '<no func>'
            w('    CREF 0x%X  %s  func=%s' % (r, ida_name.get_name(r) or '', fnm))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)