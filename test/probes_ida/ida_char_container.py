# ida_char_container.py -- 找 CCharacter 的容器与 id/name 字段
#
# 背景: CCharacter 的实例没有可直接遍历的静态容器(不像 CGameState+0x310 那样),
# 所以先静态分析它的构造函数与调用者, 找出谁持有这些对象。
#
# 已知:
#   CCharacter 虚表 RVA 0x297EA60
#   构造函数 0x140F9EC50 (584 字节), 调用者 0x1406B7260 / 0x140FA0A20 / 0x140FA30E0
#   构造函数里可见: +0x18 被写成 357, +0x28 起像 CString(cap 在 +0x40 = 15),
#                   +0x48 起另一个 CString(由参数 a2 构造)
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_char_container.txt'

lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=80, label=''):
    w('')
    w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [反编译失败] %s' % e)

# 1. 虚表槽
ea = BASE + 0x297EA60
w('=' * 80)
w('CCharacter 虚表 @ RVA 0x297EA60 (绝对 %#x)' % ea)
w('=' * 80)
for i in range(40):
    p = ida_bytes.get_qword(ea + i * 8)
    if p == 0:
        w('  [%2d] (0) 结束' % i)
        break
    f = ida_funcs.get_func(p)
    nm = ida_name.get_name(p) or ''
    sz = (f.end_ea - f.start_ea) if f else 0
    w('  [%2d] %#x  %-36s size=%d' % (i, p, nm[:36], sz))

# 2. 构造函数
decomp(0x140F9EC50, 90, 'CCharacter 构造函数')

# 3. 构造函数的所有调用者
w('')
w('=' * 80)
w('调用 CCharacter 构造函数的函数')
w('=' * 80)
callers = []
for x in idautils.XrefsTo(0x140F9EC50, 0):
    f = ida_funcs.get_func(x.frm)
    if f is None: continue
    if f.start_ea in [c[0] for c in callers]: continue
    callers.append((f.start_ea, f.end_ea - f.start_ea))
    w('  %#x  size=%d  name=%s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))

for st, sz in callers[:6]:
    decomp(st, 70, '调用者')

# 4. 谁引用了 CCharacter 虚表
w('')
w('=' * 80)
w('引用 CCharacter 虚表的函数')
w('=' * 80)
seen = set()
for x in idautils.XrefsTo(ea, 0):
    f = ida_funcs.get_func(x.frm)
    if f is None: continue
    if f.start_ea in seen: continue
    seen.add(f.start_ea)
    w('  %#x  size=%d  %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)