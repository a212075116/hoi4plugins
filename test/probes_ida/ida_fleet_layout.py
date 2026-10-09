# ida_fleet_layout.py -- 定位 CFleet 的构造函数 / 容器 / 字段
#
# 已知(来自 reports/vt_list.json, IDA 从 RTTI 导出):
#     CFleet::`vftable'  RVA 0x2962A18 (n=10)  和  0x2962A70 (n=6)
# CFleet 继承 CReferenceObject, 所以 +0x08 应该是 country tag。
#
# 目标: 找到创建 CFleet 并用它的数组/管理器, 以及可能的名字字段。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_fleet_layout.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=200, label=''):
    w('')
    w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

def vt_ea(rva):
    return BASE + rva

# 1) 虚表里每个槽的函数, 以及虚表的引用者
for rva in (0x2962A18, 0x2962A70):
    va = vt_ea(rva)
    w('=' * 84)
    w('CFleet 虚表 RVA %#x  (VA %#x)' % (rva, va))
    w('=' * 84)
    try:
        nm = ida_name.get_name(va) or ''
        w('  名字: %s' % nm)
        # 虚表前面的 -8 应该是 COL
        col = ida_bytes.get_qword(va - 8)
        w('  -8 处(COL) = %#x  name=%s' % (col, ida_name.get_name(col) or ''))
    except Exception as e:
        w('  [读取失败] %s' % e)
    w('')
    w('  --- 引用该虚表的函数(构造函数候选) ---')
    ctors = set()
    for x in idautils.XrefsTo(va, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        w('    %#x  size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))
        ctors.add(f.start_ea)
    w('')
    for c in sorted(ctors):
        decomp(c, 60, '构造函数候选')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s  行数=%d' % (OUT, len(lines)))