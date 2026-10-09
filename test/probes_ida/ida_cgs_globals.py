import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_lines, ida_name, ida_bytes

def out(s): print("[G4] " + str(s))
base = idaapi.get_imagebase()

# 1) CCurrentGameState 的 vftable 地址
for nm in ["??_7CCurrentGameState@@6B@", "??_7CCurrentGameState@@6B@_0", "??_7CGameState@@6B@", "??_7CGameState@@6B@_0"]:
    ea = idc.get_name_ea_simple(nm)
    out("vtable %-32s = 0x%X  (rva 0x%X)" % (nm, ea, ea - base if ea != idaapi.BADADDR else 0))

# 2) 全局变量 qword_14332F260 的所有引用
g = 0x14332F260
out("=" * 60)
out("全局 0x%X (qword_14332F260) 的引用：" % g)
c = 0
for xr in idautils.DataRefsTo(g):
    f = ida_funcs.get_func(xr)
    nm = idc.get_func_name(f.start_ea) if f else "?"
    dis = ida_lines.tag_remove(ida_lines.generate_disasm_line(xr, 0) or "")
    out("   data-ref 0x%X  in %s   | %s" % (xr, nm, dis))
    c += 1
    if c > 20: break
out("   total data refs = %d" % c)

# 3) 看 CCurrentGameState 的虚表前后 (确认边界)
vt = idc.get_name_ea_simple("??_7CCurrentGameState@@6B@")
if vt != idaapi.BADADDR:
    out("=" * 60)
    out("CCurrentGameState 虚表内容 (0x%X 起 24 个 qword)：" % vt)
    for i in range(24):
        v = ida_bytes.get_qword(vt + i * 8)
        nm2 = idc.get_name(v) if v else ""
        out("   [%2d] +0x%02X: 0x%X  %s" % (i, i * 8, v, nm2))
    out("   --- 虚表前 2 个 qword (应为 COL 指针) ---")
    for i in (-2, -1):
        v = ida_bytes.get_qword(vt + i * 8)
        out("   [%d]: 0x%X  %s" % (i, v, idc.get_name(v) if v else ""))