# -*- coding: utf-8 -*-
import idc
# ida_camera8.py -- 反编译 getter sub_140DC53B0, 并找 cam+0x6D0 / cam+0x6D4 的读写点
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera8.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=250, label=''):
    w(''); w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [无结果]')
    except Exception as e: w('    [失败] %s' % e)

w('=' * 88)
w('一、getter sub_140DC53B0 (obj 的虚表 +0x130) 返回什么')
w('=' * 88)
decomp(0x140DC53B0, 200, 'getter')

w('')
w('=' * 88)
w('二、obj 的虚表 0x2968FF0 全部槽(前 60)')
w('=' * 88)
VT = BASE + 0x2968FF0
k = 0
while k < 60:
    p = ida_bytes.get_qword(VT + k * 8)
    seg = ida_segment.getseg(p)
    if p == 0 or seg is None or not (seg.perm & 1): break
    w('  [%2d] off +%#05x  %#x  %s' % (k, k * 8, p, ida_name.get_name(p) or ''))
    k += 1
w('  槽数=%d' % k)

w('')
w('=' * 88)
w('三、全二进制里出现 6D0h / 6D4h / 6F0h 偏移作为立即数的指令(在反汇编文本里搜)')
w('=' * 88)
pats = ['+6D0h', '+6D4h', '+6D8h', '+6DCh', '+6F0h', '+6F4h', '6D0h', '6D4h']
hits = {}
for seg_ea in idautils.Segments():
    s = ida_segment.getseg(seg_ea)
    if s is None: continue
    if not (s.perm & 1): continue
    if s.perm & 2: continue   # 跳过数据段, 只看代码
    ea = s.start_ea
    while ea < s.end_ea:
        f = ida_funcs.get_func(ea)
        if f is None:
            ea = ida_segment.get_next_seg(ea) or s.end_ea
            break
        for item in idautils.FuncItems(f.start_ea):
            d = idc.GetDisasm(item)
            for pt in ('+6D0h', '+6D4h'):
                if pt in d:
                    hits.setdefault(f.start_ea, []).append((item, d))
        ea = f.end_ea
w('  命中函数数 = %d' % len(hits))
for fea in sorted(hits):
    w('')
    w('  ### %s @ %#x  (%d 处)' % (ida_funcs.get_func_name(fea), fea, len(hits[fea])))
    for item, d in hits[fea][:8]:
        w('      %#x  %s' % (item, d))

w('')
w('=' * 88)
w('四、这些函数的反编译(前 8 个)')
w('=' * 88)
for fea in sorted(hits)[:8]:
    decomp(fea, 250, ida_funcs.get_func_name(fea))

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print(''); print('[写出] %s 行数=%d' % (OUT, len(lines)))
