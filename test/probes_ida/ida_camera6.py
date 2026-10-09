# -*- coding: utf-8 -*-
# ida_camera6.py -- dump debug_zoom/cameraclamp/debug_lockcamera 引用点附近的反汇编
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, ida_segment, ida_ua, idc
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera6.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def dis(start, count):
    ea = start
    out = []
    for _ in range(count):
        try:
            out.append('    %#x  %s' % (ea, idc.GetDisasm(ea)))
        except Exception:
            break
        nxt = idc.next_head(ea, ea + 16)
        if nxt <= ea: break
        ea = nxt
    return out

TARGETS = [
    ('debug_zoom', 0x1427298e0),
    ('cameraclamp', 0x14272a3c0),
    ('debug_lockcamera', 0x142729f50),
    ('Camera clamp is now ', 0x14272fe60),
    ('Camera movement unlocked!', 0x14272f4a0),
    ('Camera movement locked!', 0x14272f4c0),
]
for name, ea in TARGETS:
    w('=' * 90)
    w('字符串 %r @ %#x' % (name, ea))
    w('=' * 90)
    xs = list(idautils.XrefsTo(ea, 0))
    w('  引用数 = %d' % len(xs))
    for x in xs:
        f = ida_funcs.get_func(x.frm)
        w('')
        w('  --- 引用点 %#x  所在函数 %s ---' % (x.frm, ida_funcs.get_func_name(f.start_ea) if f else '(无)'))
        # 往前找函数入口附近的字符串比较结构, 从引用点前 0x60 到后 0x120
        st = x.frm - 0x60
        for ln in dis(st, 60): w(ln)
    w('')

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print(''); print('[写出] %s 行数=%d' % (OUT, len(lines)))
