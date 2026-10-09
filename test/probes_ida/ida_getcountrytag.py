# ida_getcountrytag.py -- 反编译 GetCountryTag/GetIndex 的实现
#
# 关键断言(IDA 字符串):
#   OutCountries[ i ]->GetCountryTag().GetIndex() == i
#   Tried to access countrytag outside of array, could be semi-serious - Johan L
# 引用它们的函数就是 CCountryTag 的取值实现。
#
# 目标: 确定 CCountryTag 与"tag 字符串(ABY)"之间的对应关系。
import idaapi, idautils, ida_funcs, ida_hexrays, ida_name, ida_bytes

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_getcountrytag.txt'
base = idaapi.get_imagebase()

STR_EAS = [
    0x1427EA598,   # OutCountries[ i ]->GetCountryTag().GetIndex() == i
    0x1427EA3C0,   # Tried to access countrytag outside of array
    0x1427E3948,   # Overlord.GetCountryTag().IsValid()
    0x1427E9A78,   # GetCountryTag() != ReturningTag
    0x1427E9E28,   # pVariant->GetCreator() == GetCountryTag()
    0x142727740,   # "countrytag"
    0x1427294A8,   # "<CountryTag>"
]

lines = []
def w(s):
    lines.append(s)
    print(s, flush=True)

seen = set()
for sea in STR_EAS:
    w('=' * 72)
    w('# 字符串 %#x' % sea)
    w('=' * 72)
    for xr in idautils.XrefsTo(sea, 0):
        f = ida_funcs.get_func(xr.frm)
        if f is None:
            w('  (无函数) %#x' % xr.frm)
            continue
        if f.start_ea in seen:
            w('  (已反编译) %#x %s' % (f.start_ea, ida_name.get_name(f.start_ea) or '?'))
            continue
        seen.add(f.start_ea)
        w('  --- 函数 %#x  %s   大小 %d' % (f.start_ea, ida_name.get_name(f.start_ea) or '?', f.end_ea - f.start_ea))
        try:
            cf = ida_hexrays.decompile(f.start_ea)
            if cf is not None:
                w(str(cf))
        except Exception as e:
            w('  (反编译失败: %s)' % e)
        w('')

open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines))
print('written: ' + OUT, flush=True)
idaapi.qexit(0)