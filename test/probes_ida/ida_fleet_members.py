# -*- coding: utf-8 -*-
# ida_fleet_members.py -- 定位 CFleet 内部持有的容器 (舰船 / 特遣舰队)

#

# 已知 (reports/ida_fleet_layout.txt):

#   CFleet 虚表 0x2962A18 (n=10) 与 0x2962A70 (n=6)

#   对象大小 0x130; 名字 CString 在 +0xE0; 所属国家 CCountry* 在 +0xA8

#   +0x50 / +0x70 / +0xA0 初值为 off_143085170 (CPdxArray 空哨兵)

#   CFleet 创建包装 sub_140D545A0; 加入舰船 sub_140D51010(fleet, ship, 1)

#

# 目标: 把 CFleet 的每个虚函数与成员操作函数反编译出来, 找出舰船/特遣舰队的容器与元素数偏移。

import idaapi, idautils, ida_funcs, ida_name, ida_bytes, ida_hexrays


BASE = idaapi.get_imagebase()

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_fleet_members.txt'

lines = []

def w(s):

    lines.append(str(s))

    print(s)



def decomp(ea, n=180, label='', sub=False):

    w('')

    w('--- %s %#x ---' % (label, ea))

    try:

        cf = ida_hexrays.decompile(ea)

        if cf:

            for ln in str(cf).split(chr(10))[:n]:

                w(('        ' if sub else '    ') + ln)

        else:

            w('    [反编译无结果]')

    except Exception as e:

        w('    [失败] %s' % e)



def fname(ea):

    f = ida_funcs.get_func(ea)

    if f is None:

        return None, ''

    return f, (ida_funcs.get_func_name(f.start_ea) or ida_name.get_name(f.start_ea) or '')



VTS = ((0x2962A18, 10), (0x2962A70, 6))

slot_funcs = []

for rva, n in VTS:

    va = BASE + rva

    w('=' * 90)

    w('CFleet 虚表 RVA %#x  (VA %#x)  槽位数 %d' % (rva, va, n))

    w('=' * 90)

    for i in range(n):

        p = ida_bytes.get_qword(va + 8 * i)

        f, nm = fname(p)

        size = (f.end_ea - f.start_ea) if f else 0

        w('  槽 %2d  %#018x  size=%-6d  %s' % (i, p, size, nm))

        if f:

            slot_funcs.append((rva, i, p, nm))

    w('')



w('=' * 90)

w('逐个虚函数反编译')

w('=' * 90)

for rva, i, p, nm in slot_funcs:

    decomp(p, 150, 'vt%#x[%d] %s' % (rva, i, nm))



# 加入舰船 / 容器相关函数

EXTRA = (

    (0x140D51010, 'CFleet 加入舰船 (由容器读取点 sub_1406D2EC0 调用)'),

    (0x140D597F0, 'sub_140D597F0 (容器读取点里的判定函数)'),

    (0x140D545A0, 'CFleet 创建包装 (malloc 0x130)'),

    (0x140D503D0, 'CFleet 构造函数'),

)

w('')

w('=' * 90)

w('成员操作函数反编译')

w('=' * 90)

for ea, lab in EXTRA:

    decomp(ea, 220, lab)



with open(OUT, 'w', encoding='utf-8') as fp:

    fp.write(chr(10).join(lines))

print('')

print('[写出] %s  行数=%d' % (OUT, len(lines)))
