import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_lines, ida_name

def out(s): print("[G5] " + str(s))
base = idaapi.get_imagebase()
idc.set_ida_state(idc.IDA_STATUS_WORK) if False else None

# 1) CGameState 构造函数反汇编（捷取字段初始化部分）
f = 0x1401BFD30
out("=" * 60)
out("CGameState ctor 0x%X size=%d" % (f, idc.get_func_attr(f, idc.FUNCATTR_END) - f))
if ida_hexrays.init_hexrays_plugin():
    try:
        cf = ida_hexrays.decompile(f)
        txt = str(cf)
        lines = txt.split(chr(10))
        out("decompile lines = %d" % len(lines))
        for ln in lines[:70]:
            out("  " + ln)
    except Exception as e:
        out("decompile fail: %s" % e)

# 2) 找所有名字里带 CCountry 的函数/类型符号
out("=" * 60)
out("含 CCountry 的符号（前 40）：")
c = 0
for ea, nm in idautils.Names():
    if "CCountry" in nm and "@" in nm:
        out("   0x%X  %s" % (ea, nm))
        c += 1
        if c >= 40: break
out("   计数 = %d" % c)

# 3) 关键：找 CPdxArray<CCountry*> 的类型描述符号
out("=" * 60)
for pat in ["CPdxArray@PEAVCCountry", "DailyUpdate@CGameState", "DoCountryHourlyUpdates@CGameState"]:
    out("搜索 %s :" % pat)
    cc = 0
    for ea, nm in idautils.Names():
        if pat in nm:
            out("   0x%X  %s" % (ea, nm))
            cc += 1
            if cc >= 6: break
    out("   = %d" % cc)