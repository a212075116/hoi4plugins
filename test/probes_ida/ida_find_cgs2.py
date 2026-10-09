import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_lines, ida_xref, ida_name

def out(s): print("[G2] " + str(s))
base = idaapi.get_imagebase()

targets = [0x1401BF930, 0x1401C9500]
for t in targets:
    out("=" * 64)
    f = ida_funcs.get_func(t)
    out("func 0x%X  name=%s  size=%d" % (t, idc.get_func_name(t), f.end_ea - f.start_ea))
    out("--- callers of this func ---")
    n = 0
    for xr in idautils.CodeRefsTo(t, 0):
        cf = ida_funcs.get_func(xr)
        nm = idc.get_func_name(cf.start_ea) if cf else "?"
        out("   from 0x%X (in %s)" % (xr, nm))
        n += 1
        if n > 8: break
    out("   total refs = %d" % n)
    # 反汇编
    if ida_hexrays.init_hexrays_plugin():
        try:
            cf2 = ida_hexrays.decompile(t)
            txt = str(cf2)
            out("--- decompile (first 60 lines) ---")
            for ln in txt.split(chr(10))[:60]:
                out("  " + ln)
        except Exception as e:
            out("decompile fail: %s" % e)

# 全局搜索 CCurrentGameState 相关符号
out("=" * 64)
out("symbols containing CurrentGameState:")
for i in range(1, ida_name.get_max_ea() and 0 or 1):
    break
c = 0
for ea, nm in idautils.Names():
    if "CurrentGameState" in nm:
        out("   0x%X  %s" % (ea, nm))
        c += 1
        if c > 25: break
out("   total = %d" % c)