import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_lines, ida_bytes, ida_name, ida_xref

def out(s): print("[GS] " + str(s))

base = idaapi.get_imagebase()
CANDS = [0x1401C29A0, 0x1401BFD30]

for c in CANDS:
    out("=" * 60)
    out("candidate ctor 0x%X  size=%d  name=%s" % (c, idc.get_func_attr(c, idc.FUNCATTR_END) - c, idc.get_func_name(c)))
    f = ida_funcs.get_func(c)
    # 反汇编前 25 条
    out("--- asm (first 25) ---")
    a = c; n = 0
    while a < f.end_ea and n < 25:
        out("  0x%X: %s" % (a, ida_lines.tag_remove(ida_lines.generate_disasm_line(a, 0) or "")))
        a = idc.next_head(a, f.end_ea)
        n += 1
    # 调用者
    out("--- callers ---")
    cnt = 0
    for xr in idautils.CodeRefsTo(c, 0):
        cf = ida_funcs.get_func(xr)
        if cf is None: continue
        cnt += 1
        if cnt > 12: break
        out("  caller 0x%X (%s)  at 0x%X" % (cf.start_ea, idc.get_func_name(cf.start_ea), xr))
        # 看调用点后 30 条指令，找 mov cs:xxx, rax
        a2 = xr; m = 0
        while a2 < cf.end_ea and m < 30:
            dis = ida_lines.tag_remove(ida_lines.generate_disasm_line(a2, 0) or "")
            if a2 > xr and ("cs:" in dis or "ds:" in dis) and ("rax" in dis or "r8" in dis or "rbx" in dis):
                out("      >>> 0x%X: %s" % (a2, dis))
            a2 = idc.next_head(a2, cf.end_ea)
            m += 1
    out("  total callers = %d" % cnt)