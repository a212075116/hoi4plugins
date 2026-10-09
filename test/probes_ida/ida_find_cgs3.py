import idaapi, idc, idautils, ida_funcs, ida_hexrays, ida_lines, ida_name

def out(s): print("[G3] " + str(s))
base = idaapi.get_imagebase()

# 逐层往上追 xref，找全局变量写入
seen = set()
queue = [(0x1401BF930, 0)]
MAXD = 5
while queue:
    fn, d = queue.pop(0)
    if fn in seen or d > MAXD: continue
    seen.add(fn)
    f = ida_funcs.get_func(fn)
    if f is None: continue
    out("%s 0x%X (%s) depth=%d size=%d" % ("  " * d, fn, idc.get_func_name(fn), d, f.end_ea - f.start_ea))
    # 扫描函数体内的全局变量写入
    a = f.start_ea
    while a < f.end_ea:
        dis = ida_lines.tag_remove(ida_lines.generate_disasm_line(a, 0) or "")
        low = dis.lower()
        if ("cs:" in low or "ds:" in low) and ("mov" in low or "lea" in low):
            if any(r in low for r in ["rax","rbx","rcx","rdx","rsi","rdi","r8","r9","r10"]):
                # 只关心写入（目标在左边）
                if low.strip().startswith(("mov","lea")):
                    dst = low.split(",")[0] if "," in low else ""
                    if "cs:" in dst or "ds:" in dst:
                        out("%s   >>> 全局写入 0x%X: %s" % ("  " * d, a, dis))
        a = idc.next_head(a, f.end_ea)
    # 找调用者
    for xr in idautils.CodeRefsTo(fn, 0):
        cf = ida_funcs.get_func(xr)
        if cf and cf.start_ea not in seen:
            out("%s   caller 0x%X (%s) at 0x%X" % ("  " * d, cf.start_ea, idc.get_func_name(cf.start_ea), xr))
            queue.append((cf.start_ea, d + 1))

out("=" * 60)
out("含 GameState 的全局符号：")
c = 0
for ea, nm in idautils.Names():
    if ("GameState" in nm or "game_state" in nm) and ("qword" in nm or "dword" in nm or "byte" in nm or nm.startswith("unk")):
        out("   0x%X  %s" % (ea, nm))
        c += 1
        if c > 30: break
out("   total = %d" % c)