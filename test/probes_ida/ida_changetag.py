# ida_changetag.py -- 反编译 CChangeTagEffect, 看 tag 到底怎么存怎么改
#
# CChangeTagEffect = "改变国家 tag" 的 effect, 必然读写 tag 字段, 是揭示存储方式的最佳样本。
# 它的 vtable RVA = 0x276F848, 27 槽。
# 同时把 CCountryTagAliasEntry 也反编译(别名表, 说明 tag 如何被解析)。
import idaapi, idautils, idc, ida_funcs, ida_hexrays, ida_bytes, ida_name

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_changetag.txt'
base = idaapi.get_imagebase()

TARGETS = [
    ('CChangeTagEffect', 0x276F848, 27),
    ('CCountryTagAliasEntry', 0x27EA8D0, 9),
]

lines = []
def w(s):
    lines.append(s)
    print(s, flush=True)

def dump_class(cls, rva, nslot, decompile=True):
    vt = base + rva
    w('=' * 72)
    w('# %s  vtable RVA %#x  %d 槽' % (cls, rva, nslot))
    w('=' * 72)
    for slot in range(nslot):
        ea = vt + slot * 8
        fn = ida_bytes.get_qword(ea)
        nm = ida_name.get_name(fn) or '?'
        f = ida_funcs.get_func(fn)
        sz = (f.end_ea - f.start_ea) if f else 0
        w('slot %2d  fn=%#x  size=%-6d %s' % (slot, fn, sz, nm))
        if not decompile or f is None: continue
        try:
            cf = ida_hexrays.decompile(fn)
            if cf is not None:
                w(str(cf))
        except Exception as e:
            w('  (反编译失败: %s)' % e)
        w('')
    w('')

for cls, rva, n in TARGETS:
    dump_class(cls, rva, n)

# 字符串 aCountryTags / aCountryTag 的引用点, 反编译那些函数
w('=' * 72)
w('# 引用 aCountryTag* 字符串的函数')
w('=' * 72)
STR_EAS = [0x142727C08, 0x142727D50, 0x14272A7A0, 0x14272B960]
seen = set()
for sea in STR_EAS:
    for xr in idautils.XrefsTo(sea, 0):
        f = ida_funcs.get_func(xr.frm)
        if f is None: continue
        if f.start_ea in seen: continue
        seen.add(f.start_ea)
        w('--- %#x  %s  (str %#x)' % (f.start_ea, ida_name.get_name(f.start_ea) or '?', sea))
        try:
            cf = ida_hexrays.decompile(f.start_ea)
            if cf is not None: w(str(cf))
        except Exception as e:
            w('  (反编译失败: %s)' % e)
        w('')

open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines))
print('written: ' + OUT, flush=True)
idaapi.qexit(0)