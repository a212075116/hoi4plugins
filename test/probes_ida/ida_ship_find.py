# -*- coding: utf-8 -*-
# ida_ship_find.py -- CShip / CTaskForce 的构造函数与 +0xA0 访问点
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, ida_hexrays
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_ship_find.txt'
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
def fnam(ea):
    f = ida_funcs.get_func(ea)
    if f is None: return None, ''
    return f, (ida_funcs.get_func_name(f.start_ea) or ida_name.get_name(f.start_ea) or '')

for rva, tag in ((0x2957F28, 'CShip_a'), (0x2957F90, 'CShip_b'), (0x2962F70, 'CTaskForce_a')):
    va = BASE + rva
    w('=' * 88)
    w('%s  RVA %#x  (VA %#x)' % (tag, rva, va))
    w('=' * 88)
    refs = set()
    for x in idautils.XrefsTo(va, 0):
        f, nm = fnam(x.frm)
        if f is None:
            w('  裸引用 @%#x' % x.frm); continue
        w('  引用者 %#x size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, nm))
        refs.add(f.start_ea)
    for c in sorted(refs):
        decomp(c, 160, '构造函数候选 ' + tag)
    w('')

# CTaskForce 里 +0xA0 / +0xB8 的访问者: 在 CTaskForce 构造里找
w('=' * 88)
w('CFleet 里 task_force 容器 (+0xB8) 的使用点')
w('=' * 88)
for rva in (0x2962A18, 0x2962A70):
    va = BASE + rva
    for i in range(12):
        p = ida_bytes.get_qword(va + 8 * i)
        f, nm = fnam(p)
        if f: decomp(f.start_ea, 120, 'CFleet vt %#x[%d] %s' % (rva, i, nm))

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
