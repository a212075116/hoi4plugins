# -*- coding: utf-8 -*-
# 读 apply_cdecl / parse_decls / print_type 的准确签名
import os, json, traceback
import ida_pro, ida_auto, ida_typeinf
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    for nm in ['apply_cdecl', 'parse_decls', 'print_type', 'print_decls',
               'get_named_type', 'get_idati', 'idc_parse_decl']:
        obj = getattr(ida_typeinf, nm, None)
        w('=' * 60)
        w('### %s  ->  %s' % (nm, obj))
        d = getattr(obj, '__doc__', None)
        w('  doc: %s' % (d if d else '<无>'))
        w('')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)