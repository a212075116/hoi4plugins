# -*- coding: utf-8 -*-
# ida_camera5.py -- 追 TUT_MOVE_CAMERA 事件的监听者, 找真正操作摄像机的代码
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera5.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=350, label=''):
    w(''); w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [无结果]')
    except Exception as e: w('    [失败] %s' % e)

NEED = ['TUT_MOVE_CAMERA', 'TUT_MOVE', 'camera_position', 'camera_look_at', 'camera_tilt', 'min_zoom', 'max_zoom', 'camera_strategy']

w('=' * 90)
w('一、目标字符串及其引用者')
w('=' * 90)
xrefs = {}
for s in idautils.Strings():
    v = str(s)
    if v not in NEED: continue
    w('')
    w('### %r @ %#x' % (v, s.ea))
    for x in idautils.XrefsTo(s.ea, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None:
            w('   裸引用 %#x' % x.frm); continue
        fn = ida_funcs.get_func_name(f.start_ea)
        sz = f.end_ea - f.start_ea
        w('   引用者 %#x size=%-7d %s' % (f.start_ea, sz, fn))
        if sz < 40000:
            xrefs.setdefault(f.start_ea, set()).add(v)

w('')
w('=' * 90)
w('二、引用者反编译(排除巨型函数)')
w('=' * 90)
for ea in sorted(xrefs):
    decomp(ea, 350, '引用 ' + ','.join(sorted(xrefs[ea])))

w('')
w('=' * 90)
w('三、vfunc_9 里用到的 qword_14332F6A0 是什么(它被当成渲染器调用)')
w('=' * 90)
for nm in ['qword_14332F6A0']:
    for i in range(ida_name.get_nlist_size()):
        s = ida_name.get_nlist_name(i)
        if s == nm:
            ea = ida_name.get_nlist_ea(i)
            w('  %s @ %#x' % (nm, ea))
            for x in idautils.XrefsTo(ea, 0):
                f = ida_funcs.get_func(x.frm)
                w('     被引用于 %#x  %s' % (x.frm, ida_funcs.get_func_name(f.start_ea) if f else '(非函数)'))

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print(''); print('[写出] %s 行数=%d' % (OUT, len(lines)))
