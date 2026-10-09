# ida_char_mgr2.py -- 完整反编译两个 CCharacter 创建函数, 找出管理器来源
#
# 调用点: sub_1410DCDF0 在 0x1410DD09E 调用 sub_1406B70B0
#         sub_140357BE0 在 0x140357FD9 调用 sub_1406B7510
# 两者附近没有直接加载全局, 说明 a1 是算出来的或来自参数。完整反编译看清。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_char_mgr2.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def disasm_range(start, end, label):
    w('')
    w('--- %s  反汇编 %#x..%#x ---' % (label, start, end))
    ea = start
    while ea < end and ea != idc.BADADDR:
        w('  %#x  %s' % (ea, idc.generate_disasm_line(ea, 0)))
        ea = idc.next_head(ea)

def decomp_full(ea, label):
    w('')
    w('=' * 78)
    w('%s  %#x  完整反编译' % (label, ea))
    w('=' * 78)
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10)):
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

disasm_range(0x1410DD060, 0x1410DD0C0, 'sub_1410DCDF0 调用点')
disasm_range(0x140357FA0, 0x140358000, 'sub_140357BE0 调用点')
decomp_full(0x1410DCDF0, '创建函数 A')
decomp_full(0x140357BE0, '创建函数 B')

# 找 sub_1406B2A10 (数组追加) 与 sub_1406B4C20 (取对象) 的定义, 了解容器结构
for f, lbl in ((0x1406B2A10, '数组追加'), (0x1406B4C20, '取对象'), (0x1406B4CA0, '取元素')):
    decomp_full(f, lbl)

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)