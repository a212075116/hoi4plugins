# ida_tagconv.py -- 反编译 tag 转换函数, 确定 CCountryTag 的编码方式
#
# 线索来自 CChangeTagEffect:
#   slot2 读 *(DWORD*)(this+32)  ==> tag 是 4 字节值
#   slot1 调 sub_1424BC260(tag)  ==> 该函数负责 tag -> 字符串
# 只要看懂这个函数, tag 的编码就确定了, 也就能反推 CCountry 里该怎么取 tag。
import idaapi, idautils, ida_funcs, ida_hexrays, ida_name, ida_bytes

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_tagconv.txt'
base = idaapi.get_imagebase()

TARGETS = [
    0x1424BC260,   # tag -> CString (CChangeTagEffect slot1 调用)
    0x14053FA80,   # CChangeTagEffect 里读 tag 字符串
    0x1405419C0,   # 上面用到的辅助
    0x1424C5C60,   # 上面用到的辅助
]

lines = []
def w(s):
    lines.append(s)
    print(s, flush=True)

for ea in TARGETS:
    w('=' * 72)
    w('# %#x  %s' % (ea, ida_name.get_name(ea) or '?'))
    w('=' * 72)
    f = ida_funcs.get_func(ea)
    if f is None:
        w('  (不是函数起点)')
        w('')
        continue
    w('  范围 %#x..%#x  大小 %d' % (f.start_ea, f.end_ea, f.end_ea - f.start_ea))
    # 调用者
    w('  调用者:')
    n = 0
    for xr in idautils.XrefsTo(f.start_ea, 0):
        if xr.type in (16, 17, 18, 19, 20, 21):   # 调用类 xref
            cf = ida_funcs.get_func(xr.frm)
            w('      %#x  %s' % (xr.frm, ida_name.get_name(cf.start_ea) if cf else '?'))
            n += 1
            if n >= 15: break
    if n == 0: w('      (无调用者)')
    try:
        cf2 = ida_hexrays.decompile(f.start_ea)
        if cf2 is not None: w(str(cf2))
        else: w('  (反编译返回空)')
    except Exception as e:
        w('  (反编译失败: %s)' % e)
    w('')

open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines))
print('written: ' + OUT, flush=True)
idaapi.qexit(0)