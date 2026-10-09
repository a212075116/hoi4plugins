# ida_fleet_owner.py -- 找 CFleet 的持有者(容器) 和 名字来源
#
# sub_140D545A0(a1) 创建 CFleet:
#   malloc(0x130) -> sub_140D503D0(obj, a1) 构造
#   v8 = sub_140D55DC0();  v9 = sub_140AF1C70(v8, &v14, a1, 0)
#   if (obj + 0xE0 != v9) { ... }   <- 设置名字(+0xE0)
#
# 所以: sub_140D55DC0() 是名字来源, a1 是 fleet 的某些输入。
# 找 sub_140D545A0 的调用者 => 容器。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_fleet_owner.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=110, label=''):
    w('')
    w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

for root, lbl in ((0x140D545A0, 'CFleet 创建函数'), (0x140D55DC0, '名字来源函数')):
    w('=' * 80)
    w('%s %#x 的调用者' % (lbl, root))
    w('=' * 80)
    f = ida_funcs.get_func(root)
    if f: w('  自身: %#x size=%d' % (f.start_ea, f.end_ea - f.start_ea))
    for x in idautils.XrefsTo(root, 0):
        g = ida_funcs.get_func(x.frm)
        if g is None: continue
        w('    %#x  size=%-6d %s' % (g.start_ea, g.end_ea - g.start_ea, ida_funcs.get_func_name(g.start_ea)))
    w('')

decomp(0x140D55DC0, 40, '名字来源函数本体')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)