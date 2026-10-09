# -*- coding: utf-8 -*-
# ida_army_find.py -- CArmy / CUnit 构造函数与虚表引用者
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_army_find.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def decomp(ea, n=200, label=''):
    w(''); w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]: w('    ' + ln)
        else: w('    [反编译无结果]')
    except Exception as e: w('    [失败] %s' % e)

VTS = [(0x295A2B0,'CArmy_a'), (0x295A490,'CArmy_b'), (0x295A500,'CArmy_c'), (0x295A548,'CArmy_d'),
       (0x29530D8,'CUnit_a'), (0x29532B0,'CUnit_b'), (0x2953320,'CUnit_c')]

for rva, tag in VTS:
    va = BASE + rva
    w('=' * 90)
    w('%s  RVA %#x  VA %#x' % (tag, rva, va))
    w('=' * 90)
    info = ida_bytes.get_qword(va - 8)
    if info: w('  -0x8 (COL) = %#x' % info)
    refs = set()
    for x in idautils.XrefsTo(va, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None:
            w('  裸引用 @%#x' % x.frm); continue
        w('  引用者 %#x size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))
        refs.add(f.start_ea)
    for c in sorted(refs)[:6]:
        decomp(c, 170, '候选 ' + tag)
    w('')

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
