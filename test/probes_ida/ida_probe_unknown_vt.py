# -*- coding: utf-8 -*-
# 检查栈上高频指针 0x2715B00/0x2715B08 到底是不是虚表
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_nalt, idautils, ida_funcs
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    for rva in cfg['rvas']:
        ea = base + rva
        w('')
        w('##### RVA 0x%X  =>  EA 0x%X' % (rva, ea))
        w('   name    = %s' % (ida_name.get_name(ea) or '<none>'))
        seg = ida_segment.getseg(ea)
        w('   segment = %s' % (ida_segment.get_segm_name(seg) if seg else '<none>'))
        w('   flags   = 0x%X   is_code=%s' % (ida_bytes.get_flags(ea), ida_bytes.is_code(ida_bytes.get_flags(ea))))
        # 往前看是否紧邻一个 COL（说明它是某虚表的起始）
        import struct
        prev = ida_bytes.get_qword(ea - 8)
        w('   [ea-8]  = 0x%X   %s' % (prev, ida_name.get_name(prev) or '<none>'))
        # 当作虚表解 12 个槽位
        w('   --- 若视为虚表，前 12 槽 ---')
        for k in range(12):
            p = ida_bytes.get_qword(ea + k * 8)
            s2 = ida_segment.getseg(p)
            code = bool(s2 and (s2.perm & 1))
            w('      [%2d] 0x%-12X %-6s %s' % (k, p, 'code' if code else 'NOCODE',
               ida_name.get_name(p) or '<noname>'))
        # 谁引用了它
        refs = list(idautils.DataRefsTo(ea))
        w('   data refs = %d' % len(refs))
        for r in refs[:8]:
            fn = ida_funcs.get_func(r)
            w('      0x%X  %s' % (r, ida_name.get_name(fn.start_ea) if fn else '<nofunc>'))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)