# -*- coding: utf-8 -*-
# ida_camera4.py -- 反编译 CTutMoveCameraTo 全部虚函数 + move_camera_to 实现全body + 找 CCamera 的用法
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera4.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=400, label=''):
    w(''); w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [无结果]')
    except Exception as e: w('    [失败] %s' % e)

VT = 0x142a27e08   # ??_7CTutMoveCameraTo@@6B@
w('=' * 90)
w('一、CTutMoveCameraTo 全部虚函数')
w('=' * 90)
k = 0
while k < 20:
    p = ida_bytes.get_qword(VT + k * 8)
    seg = ida_segment.getseg(p)
    if p == 0 or seg is None or not (seg.perm & 1): break
    nm = ida_name.get_name(p) or ''
    w('  [%2d] %#x  %s' % (k, p, nm))
    k += 1
for j in range(k):
    fn = ida_bytes.get_qword(VT + j * 8)
    nm = ida_name.get_name(fn) or ''
    if nm == '_purecall' or nm == '_guard_check_icall_nop': continue
    decomp(fn, 400, 'CTutMoveCameraTo::vfunc_%d' % j)

w('')
w('=' * 90)
w('二、move_camera_to 的实现 sub_1419CA5C0 全 body')
w('=' * 90)
decomp(0x1419CA5C0, 700, 'move_camera_to 实现')

w('')
w('=' * 90)
w('三、CCamera 类是否存在 RTTI')
w('=' * 90)
n = ida_name.get_nlist_size()
for i in range(n):
    s = ida_name.get_nlist_name(i)
    if not s: continue
    if 'CCamera' in s and '@@' in s:
        w('  %#x  %s' % (ida_name.get_nlist_ea(i), s))

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
