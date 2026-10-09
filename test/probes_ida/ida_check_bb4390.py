# ida_check_bb4390.py -- 确认 sub_140BB4390 返回什么, 并找 CFleet 数组的真实偏移
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_check_bb4390.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=80, label=''):
    w('')
    w('=' * 76)
    w('%s  %#x' % (label, ea))
    w('=' * 76)
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

decomp(0x140BB4390, 60, 'sub_140BB4390 (sub_1406D2EC0 里用来取 v6 的)')
decomp(0x140BB4E70, 60, 'sub_140BB4E70')

# CCountry 虚表是 0x27E7360; 找 CCountry 里 size/ptr 成对出现的地方
# 直接看 CCountry 的构造函数(写 CCountry::vftable 的那个)
w('')
w('=' * 76)
w('引用 CCountry 虚表的函数(构造函数)')
w('=' * 76)
for x in idautils.XrefsTo(BASE + 0x27E7360, 0):
    f = ida_funcs.get_func(x.frm)
    if f is None: continue
    w('  %#x size=%-6d %s' % (f.start_ea, f.end_ea - f.start_ea, ida_funcs.get_func_name(f.start_ea)))

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)