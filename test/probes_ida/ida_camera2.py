# -*- coding: utf-8 -*-
# ida_camera2.py -- 追摄像机属性名的注册者与 CTutMoveCameraTo / CCameraControlStrategy 的实现
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment, ida_nalt
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera2.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=200, label='', depth=0):
    w('')
    w('%s--- %s %#x ---' % ('  ' * depth, label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('%s    %s' % ('  ' * depth, ln))
        else: w('%s    [反编译无结果]' % ('  ' * depth))
    except Exception as e: w('%s    [失败] %s' % ('  ' * depth, e))

TARGETS = {
    'camera': 0x142ae76fc,
    'cameraMove': 0x142ae76d8,
    'camera_look_at': 0x142ae9548,
    'camera_position': 0x142ae9560,
    'camera_rotation_speed': 0x142ae97a8,
    'camera_speed': 0x142aed1e0,
    'camera_tilt': 0x142aed218,
    'camera_strategy': 0x142aed228,
    'min_zoom': 0x142ae9600,
    'max_zoom': 0x142ae9610,
    'zoom_speed': 0x142ae97e0,
    'centered_zoom_in': 0x142aed1f0,
    'move_camera_to': 0x142a286e0,
}

w('=' * 90)
w('一、各属性名的引用者(排除巨型控制台分发函数 sub_1400036F0)')
w('=' * 90)
callers = {}
for nm, ea in TARGETS.items():
    w('')
    w('### %r @ %#x' % (nm, ea))
    got = 0
    for x in idautils.XrefsTo(ea, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None:
            w('   裸引用 %#x [%s]' % (x.frm, ida_bytes.get_bytes(x.frm - 8, 24))); continue
        fn = ida_funcs.get_func_name(f.start_ea)
        w('   引用者 %#x size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, fn))
        if f.end_ea - f.start_ea < 40000:
            callers.setdefault(f.start_ea, set()).add(nm)
        got += 1
    if got == 0: w('   (无引用)')

w('')
w('=' * 90)
w('二、这些引用者的反编译')
w('=' * 90)
for ea in sorted(callers):
    decomp(ea, 200, '引用 ' + ','.join(sorted(callers[ea])))

w('')
w('=' * 90)
w('三、CTutMoveCameraTo 与 CCameraControlStrategy 的虚表内容')
w('=' * 90)
for name, vtea in [('CTutMoveCameraTo', 0x142a27e08), ('CCameraControlStrategy', 0x142afda60)]:
    w('')
    w('### %s @ %#x' % (name, vtea))
    col = ida_bytes.get_qword(vtea - 8)
    w('    COL = %#x' % col)
    k = 0
    while k < 40:
        p = ida_bytes.get_qword(vtea + k * 8)
        seg = ida_segment.getseg(p)
        if p == 0 or seg is None or not (seg.perm & 1): break
        w('    [%2d] %#x  %s' % (k, p, ida_name.get_name(p) or ''))
        k += 1
    w('    槽数 = %d' % k)
    # 每个槽的反编译(前 8 个)
    for j in range(min(k, 8)):
        fn = ida_bytes.get_qword(vtea + j * 8)
        decomp(fn, 90, '%s::vfunc_%d' % (name, j))

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
