# -*- coding: utf-8 -*-
# 只读核对：打开数据库后报告签名列表与函数规模
import os, json
import ida_funcs, ida_pro, ida_nalt, ida_kernwin, ida_auto

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
try:
    f.write('kernel=%s\n' % ida_kernwin.get_kernel_version())
    f.write('input=%s\n' % ida_nalt.get_input_file_path())
    ida_auto.auto_wait()
    f.write('func_qty=%d\n' % ida_funcs.get_func_qty())
    n = ida_funcs.get_idasgn_qty()
    f.write('idasgn_qty=%d\n' % n)
    for i in range(n):
        f.write('  [%d] %s\n' % (i, ida_funcs.get_idasgn_desc_with_matches(i)))
except Exception:
    import traceback; f.write('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)