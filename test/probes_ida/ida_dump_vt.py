# -*- coding: utf-8 -*-
# 直接 dump 可疑虚表地址，看真实内容
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_funcs, ida_nalt, idautils
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    for ea in cfg['eas']:
        w('')
        w('##### EA 0x%X' % ea)
        w('   name = %s' % (ida_name.get_name(ea) or '<none>'))
        seg = ida_segment.getseg(ea)
        w('   seg  = %s' % (ida_segment.get_segm_name(seg) if seg else '<none>'))
        w('   往前看 4 个 qword:')
        for k in range(-4, 0):
            v = ida_bytes.get_qword(ea + k * 8)
            w('      [%d] 0x%-14X %s' % (k, v, ida_name.get_name(v) or ''))
        w('   虚表本体 12 个 qword:')
        for k in range(12):
            v = ida_bytes.get_qword(ea + k * 8)
            seg2 = ida_segment.getseg(v)
            code = bool(seg2 and (seg2.perm & 1))
            w('      [%2d] 0x%-14X %-5s %s' % (k, v, 'code' if code else 'NO',
              ida_name.get_name(v) or ''))
        # 谁引用了它
        refs = list(idautils.DataRefsTo(ea))
        w('   被引用 %d 次:' % len(refs))
        for rr in refs[:6]:
            fn = ida_funcs.get_func(rr)
            w('      0x%X  %s' % (rr, ida_name.get_name(fn.start_ea) if fn else '<nofunc>'))
        w('')
        # 对比：真正应该是 exception@std 虚表的位置在哪
        w('   --- 搜索名称含 exception 的 vftable 符号 ---')
        n = ida_name.get_nlist_size()
        cnt = 0
        for i in range(n):
            s2 = ida_name.get_nlist_name(i)
            if s2 and s2.startswith('??_7') and 'exception' in s2:
                w('      0x%X  %s' % (ida_name.get_nlist_ea(i), s2))
                cnt += 1
                if cnt > 10: break
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)