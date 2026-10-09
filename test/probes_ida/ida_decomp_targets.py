# -*- coding: utf-8 -*-
import os, json, traceback
import ida_pro, ida_auto, idaapi, ida_hexrays, ida_lines, ida_funcs, ida_name
import ida_bytes, idautils, idc

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()

TARGETS = json.loads(cfg.get('targets', '[]'))

try:
    ida_auto.auto_wait()
    ok = ida_hexrays.init_hexrays_plugin()
    w('Hex-Rays = %s' % ok)
    for t in TARGETS:
        ea = int(t, 16)
        fn = ida_funcs.get_func(ea)
        nm = ida_name.get_name(ea)
        w('')
        w('=' * 78)
        w('### 0x%X  %s' % (ea, nm))
        if not fn:
            w('  (非函数)'); continue
        w('  范围 0x%X - 0x%X  大小 %d' % (fn.start_ea, fn.end_ea, fn.end_ea - fn.start_ea))
        # 先列出该函数内所有字符串引用
        w('  --- 函数内引用的字符串 ---')
        seen = set()
        for item in idautils.FuncItems(fn.start_ea):
            for xr in idautils.DataRefsFrom(item):
                s = ida_bytes.get_strlit_contents(xr, -1, 0)
                if s:
                    try:
                        txt = s.decode('utf-8', 'replace')
                    except Exception:
                        continue
                    if txt not in seen and 1 < len(txt) < 160:
                        seen.add(txt)
                        w('    0x%-10X %s' % (xr, txt))
        w('  --- 伪代码 ---')
        try:
            cf = ida_hexrays.decompile(fn.start_ea)
            if cf:
                body = str(cf)
                lines = body.split(chr(10))
                for ln in lines[:120]:
                    w('    ' + ln)
                if len(lines) > 120:
                    w('    ... (共 %d 行, 已截断)' % len(lines))
            else:
                w('    反编译返回空')
        except Exception as e:
            w('    反编译失败: %s' % e)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)