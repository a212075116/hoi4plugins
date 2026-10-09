# -*- coding: utf-8 -*-
# ida_camera_find.py -- 定位摄像机相关代码: cameraclamp / debug_zoom / debug_lockcamera 字符串及其引用者
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment, ida_nalt
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera_find.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=220, label=''):
    w(''); w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [反编译无结果]')
    except Exception as e: w('    [失败] %s' % e)

NEEDLES = ['cameraclamp', 'debug_zoom', 'debug_lockcamera', 'debug_nomouse', 'debug_norender', 'camera', 'Camera', 'CCamera', 'zoom']

w('=' * 90)
w('一、字符串搜索')
w('=' * 90)
found = {}
for s in idautils.Strings():
    v = str(s)
    for nd in ['cameraclamp', 'debug_zoom', 'debug_lockcamera', 'camera', 'Camera', 'zoom', 'Zoom']:
        if nd in v:
            found.setdefault(nd, []).append((s.ea, v))
            break
for k in sorted(found):
    w('')
    w('### 含 %r 的字符串 %d 条' % (k, len(found[k])))
    for ea, v in found[k][:40]:
        w('   %#x  %r' % (ea, v[:110]))

w('')
w('=' * 90)
w('二、关键字符串的交叉引用与反编译')
w('=' * 90)
KEY = ['cameraclamp', 'debug_zoom', 'debug_lockcamera']
done = set()
for s in idautils.Strings():
    v = str(s)
    if v not in KEY:
        continue
    w('')
    w('### 字符串 %r @ %#x' % (v, s.ea))
    for x in idautils.XrefsTo(s.ea, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None:
            w('   裸引用 %#x' % x.frm); continue
        w('   引用者 %#x size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))
        done.add(f.start_ea)

for ea in sorted(done):
    decomp(ea, 240)

w('')
w('=' * 90)
w('三、RTTI 里含 Camera/Zoom/Viewport 的类')
w('=' * 90)
n = ida_name.get_nlist_size()
cnt = 0
for i in range(n):
    s = ida_name.get_nlist_name(i)
    if not s or not s.startswith('??_7'):
        continue
    if any(t in s for t in ('Camera', 'Zoom', 'Viewport', 'CView', 'Renderer')):
        w('   %#x  %s' % (ida_name.get_nlist_ea(i), s))
        cnt += 1
        if cnt > 120: w('   ...(截断)'); break

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
