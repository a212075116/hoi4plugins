# -*- coding: utf-8 -*-
# 反汇编引用虚表的函数（修正 BADADDR 导入）
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_funcs, ida_bytes, ida_lines, idautils, ida_idaapi
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    for fn_ea in cfg['funcs']:
        fn = ida_funcs.get_func(fn_ea)
        w('')
        w('##### func 0x%X  %s  size=%d' % (fn_ea, ida_name.get_name(fn_ea) or '<noname>',
          (fn.end_ea - fn.start_ea) if fn else -1))
        if not fn:
            w('   no function')
            continue
        w('   --- 内部对虚表的引用 ---')
        for ea in idautils.Heads(fn.start_ea, fn.end_ea):
            for r in idautils.DataRefsFrom(ea):
                nm = ida_name.get_name(r) or ''
                if nm.startswith('??_7'):
                    w('     0x%X -> %s' % (ea, nm))
        w('   --- 反汇编（前 40 条）---')
        cnt = 0
        ea = fn.start_ea
        while ea < fn.end_ea and cnt < 40:
            w('     %08X  %s' % (ea, ida_lines.generate_disasm_line(ea, 0) or ''))
            nxt = ida_bytes.next_head(ea, fn.end_ea)
            if nxt == ida_idaapi.BADADDR or nxt <= ea:
                break
            ea = nxt
            cnt += 1
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)