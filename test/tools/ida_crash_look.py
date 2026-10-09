import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_bytes, ida_lines

def out(s):
    print("[CRASH] " + s)

rv = 0x184E73
base = idaapi.get_imagebase()
ea = base + rv
out("imagebase=0x%X  target=0x%X" % (base, ea))

f = ida_funcs.get_func(ea)
if f is None:
    out("no function at that address (maybe mid-instruction)")
    # 往回找
    for back in range(1, 64):
        f = ida_funcs.get_func(ea - back)
        if f: break
if f:
    out("function start=0x%X (rva=0x%X)  end=0x%X  size=%d" % (f.start_ea, f.start_ea - base, f.end_ea, f.end_ea - f.start_ea))
    out("name = " + idc.get_func_name(f.start_ea))
    out("target inside function, offset=+0x%X" % (ea - f.start_ea))

# 列出调用链上另外两个地址
for r in (0x1821fa, 0x1454ea, 0x180d9f, 0x12878c):
    a = base + r
    ff = ida_funcs.get_func(a)
    if ff:
        out("rva 0x%X -> func 0x%X (rva 0x%X) %s  offset=+0x%X" % (r, ff.start_ea, ff.start_ea - base, idc.get_func_name(ff.start_ea), a - ff.start_ea))
    else:
        out("rva 0x%X -> no func" % r)

# 反编译崩溃所在函数
if f and ida_hexrays.init_hexrays_plugin():
    try:
        cf = ida_hexrays.decompile(f.start_ea)
        if cf:
            txt = str(cf)
            lines = txt.split(chr(10))
            out("=== decompiled (%d lines) ===" % len(lines))
            for ln in lines[:120]:
                out("  " + ln)
    except Exception as e:
        out("decompile failed: %s" % e)

# 崩溃点的反汇编上下文
out("=== disassembly around crash ===")
for a in range(ea - 0x30, ea + 0x20, 1):
    pass
sa = ea - 0x30
while sa < ea + 0x20:
    out("  0x%X (rva 0x%X): %s" % (sa, sa - base, idc.generate_disasm_line(sa, 0)))
    sa = idc.next_head(sa, ea + 0x40)
    if sa == idc.BADADDR: break