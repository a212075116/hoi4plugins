# ida_country_gettag.py -- 反编译 CCountry 的 11 个虚函数, 找与 tag 有关的方法
#
# 路线 2: 对象里没有 tag, 那就看"取 tag 的方法"读哪里。
# 判据(可证伪): 若某函数返回 tag, 它内部必然出现 CCountryTag 或三字母常量;
#              若它只是转发到别的对象, 则能看到对该对象的字段读取。
# 同时把每个虚函数的反编译伪代码导出, 便于人工比对。
import idaapi, idautils, idc, ida_funcs, ida_hexrays, ida_bytes, ida_name
import json, os

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_country_vfuncs.txt'
VT_RVA = 0x27E7360
NSLOT = 11
base = idaapi.get_imagebase()
vt = base + VT_RVA

lines = []
def w(s):
    lines.append(s)
    print(s, flush=True)

w('# CCountry 虚函数反编译 (vtable RVA %#x, %d 槽)' % (VT_RVA, NSLOT))
w('# imagebase = %#x' % base)
w('')

for slot in range(NSLOT):
    ea = vt + slot * 8
    fn = ida_bytes.get_qword(ea)
    name = ida_name.get_name(fn) or '?'
    w('=' * 70)
    w('slot %d  @ %#x  fn=%#x  %s' % (slot, ea, fn, name))
    w('=' * 70)
    f = ida_funcs.get_func(fn)
    if f is None:
        w('  (不是函数)')
        w('')
        continue
    w('  范围 %#x..%#x  大小 %d' % (f.start_ea, f.end_ea, f.end_ea - f.start_ea))
    try:
        cf = ida_hexrays.decompile(fn)
        if cf is None:
            w('  (反编译失败)')
        else:
            txt = str(cf)
            w(txt)
    except Exception as e:
        w('  (反编译异常: %s)' % e)
    w('')

# 额外: 列出所有引用 CCountryTag 相关符号的位置
w('=' * 70)
w('# 名称里含 CountryTag 的符号, 以及它们的交叉引用')
w('=' * 70)
cnt = 0
for ea, nm in idautils.Names():
    if 'CountryTag' in nm:
        cnt += 1
        if cnt <= 40:
            w('%#x  %s' % (ea, nm))
            try:
                for xref in idautils.XrefsTo(ea, 0):
                    w('        <- %#x' % xref.frm)
            except Exception:
                pass
w('# 共 %d 个含 CountryTag 的符号' % cnt)

open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines))
print('written: ' + OUT, flush=True)
idaapi.qexit(0)