# ida_char_mgr.py -- 找 CCharacter 管理器的全局单例
#
# 线索: sub_1406B70B0(a1, a2) 里:
#   v3 = *(DWORD*)(a1+8); *(DWORD*)(a1+8) = v3+1;  v8 = v3;   <- id 就是计数器
#   sub_140FA0A20(&Memory, a2, &n73, 0);                        <- 构造对象
#   sub_1406B2A10(a1+16, &Memory);                              <- 追加进 a1+16 数组
#   sub_1406B4CA0(*(QWORD*)(a1+16) + 8*(*(DWORD*)(a1+28)-1))    <- 取回来
# 所以 a1 是管理器。往上一层找 a1 从哪来。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_char_mgr.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=60, label=''):
    w('')
    w('--- %s %#x ---' % (label, ea))
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

ROOTS = [0x1406B70B0, 0x1406B7510]
seen = set()
for root in ROOTS:
    w('=' * 78)
    w('调用 %#x 的函数' % root)
    w('=' * 78)
    for x in idautils.XrefsTo(root, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        w('  %#x  size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))
        seen.add(f.start_ea)
    w('')

for ea in sorted(seen):
    decomp(ea, 55, '上层调用者')

# 直接找: 谁把某个全局地址传给 sub_1406B70B0 / sub_1406B7510
w('')
w('=' * 78)
w('在调用点附近找被当作 a1 传入的全局地址')
w('=' * 78)
for root in ROOTS:
    for x in idautils.XrefsTo(root, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        w('  %#x 调用 %#x 于 %#x' % (f.start_ea, root, x.frm))
        # 往前看 24 条指令找 lea/mov 加载的全局
        ea2 = x.frm
        for k in range(24):
            ea2 = idc.prev_head(ea2)
            if ea2 == idc.BADADDR: break
            mnem = idc.print_insn_mnem(ea2)
            if mnem in ('lea', 'mov'):
                op = idc.get_operand_value(ea2, 1)
                if op and (op < BASE + 0x400000 or op > BASE + 0x3800000):
                    if BASE < op < BASE + 0x37ec000 and op not in (0x1406B70B0, 0x1406B7510):
                        nm = ida_name.get_name(op) or ''
                        w('       %#x: %s %s' % (ea2, mnem, nm if nm else ('%#x' % op)))
        w('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)