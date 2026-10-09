# -*- coding: utf-8 -*-
# ida_camera7.py -- 反编译摄像机命令的处理函数, 找缩放状态
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera7.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=300, label=''):
    w(''); w('=' * 88); w('--- %s  %#x ---' % (label, ea)); w('=' * 88)
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [无结果]')
    except Exception as e: w('    [失败] %s' % e)

HANDLERS = [
    ('debug_zoom 处理函数',      0x140250340),
    ('debug_lockcamera 处理函数', 0x14024C5A0),
    ('cameraclamp 处理函数',      0x140292A50),
]
for label, ea in HANDLERS:
    decomp(ea, 320, label)
    f = ida_funcs.get_func(ea)
    if f:
        w('    [函数范围 %#x - %#x, size=%d]' % (f.start_ea, f.end_ea, f.end_ea - f.start_ea))
        w('    [调用的子函数]')
        for x in idautils.CodeRefsFrom(f.start_ea, 0):
            pass
        seen = set()
        for item in idautils.FuncItems(f.start_ea):
            for x in idautils.CodeRefsFrom(item, 0):
                if ida_funcs.get_func(x) and x != f.start_ea and x not in seen:
                    seen.add(x)
                    w('       %#x  %s' % (x, ida_funcs.get_func_name(x)))

w('')
w('=' * 88)
w('全局对象 qword_14332F698 / byte_1430B2E30 的引用')
w('=' * 88)
for nm in ['qword_14332F698', 'byte_1430B2E30', 'qword_14332F6A0']:
    for i in range(ida_name.get_nlist_size()):
        s = ida_name.get_nlist_name(i)
        if s == nm:
            ea = ida_name.get_nlist_ea(i)
            w('')
            w('### %s @ %#x' % (nm, ea))
            cnt = 0
            for x in idautils.XrefsTo(ea, 0):
                f = ida_funcs.get_func(x.frm)
                w('    %#x  in %s' % (x.frm, ida_funcs.get_func_name(f.start_ea) if f else '(non-func)'))
                cnt += 1
                if cnt > 40: w('    ...(截断)'); break

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print(''); print('[写出] %s 行数=%d' % (OUT, len(lines)))
