# ida_fleet_container.py -- 找 CFleet 的创建点与容器
# 构造函数 sub_140D503D0(this, a2) 已确认: 写 CFleet::vftable, +0xE0 处放名字 CString
# 往上层追, 找出谁持有 CFleet*。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_fleet_container.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=90, label=''):
    w('')
    w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

ROOTS = [0x140D503D0, 0x140D50840]
seen = set()
for root in ROOTS:
    w('=' * 80)
    w('调用 %#x 的函数' % root)
    w('=' * 80)
    for x in idautils.XrefsTo(root, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        w('  %#x  size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))
        seen.add(f.start_ea)
    w('')

for ea in sorted(seen):
    decomp(ea, 70, '上层调用者')

# 找 CFleet 虚表的所有引用(不只函数)以及 CFleet 的字符串线索
w('')
w('=' * 80)
w('CFleet 相关的字符串常量(可能给出容器/名字来源)')
w('=' * 80)
for s in idautils.Strings():
    try:
        t = str(s)
    except Exception:
        continue
    if 'FLEET' in t or 'fleet' in t:
        w('  %#x  %s' % (s.ea, t[:100]))

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s  行数=%d' % (OUT, len(lines)))