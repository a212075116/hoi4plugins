import idaapi, idc, ida_funcs

def out(s): print("[CR] " + s)

base = idaapi.get_imagebase()
ea = base + 0x184E73
f = ida_funcs.get_func(ea)
out("func=0x%X  crash=0x%X  offset=+0x%X" % (f.start_ea, ea, ea - f.start_ea))

out("=== 崩溃点前后反汇编 ===")
a = f.start_ea + 0x300
while a < f.start_ea + 0x3A0:
    mark = "  <== CRASH" if a == ea else ""
    out("  0x%X (+0x%X): %s%s" % (a, a - f.start_ea, idc.generate_disasm_line(a, 0), mark))
    n = idc.next_head(a, f.end_ea)
    if n == idc.BADADDR or n <= a: break
    a = n