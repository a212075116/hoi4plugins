# ida_char_callers.py -- 找 CCharacter 的创建点与容器
#
# sub_1406B7260 是「malloc(0x130) + 构造 CCharacter」的函数。
# 它的调用者就是角色的创建者, 顺着它往上找就能找到容器。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_char_callers.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

ROOTS = [0x1406B7260, 0x140FA0A20, 0x140FA30E0]
seen_all = set()
for root in ROOTS:
    w('=' * 78)
    w('调用 %#x (%s) 的函数' % (root, ida_funcs.get_func_name(root)))
    w('=' * 78)
    for x in idautils.XrefsTo(root, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        nm = ida_funcs.get_func_name(f.start_ea) or ''
        w('  %#x  size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, nm))
        seen_all.add(f.start_ea)
    w('')

w('')
w('=' * 78)
w('反编译其中较小的几个(便于读懂)')
w('=' * 78)
small = sorted([(ida_funcs.get_func(a).end_ea - a, a) for a in seen_all if ida_funcs.get_func(a)])[:4]
for sz, ea in small:
    w('')
    w('--- %#x (size=%d) ---' % (ea, sz))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:70]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

# 同时找所有把 CCharacter* 存进全局/结构的模式: 查 sub_1406B4C20 (取对象指针的辅助函数)
w('')
w('=' * 78)
w('sub_1406B4C20 (被 sub_140FA0A20 用来取对象指针) 的调用者')
w('=' * 78)
n = 0
for x in idautils.XrefsTo(0x1406B4C20, 0):
    f = ida_funcs.get_func(x.frm)
    if f is None: continue
    w('  %#x  %s' % (f.start_ea, ida_funcs.get_func_name(f.start_ea)))
    n += 1
    if n > 40: break

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)