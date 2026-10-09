import os, sys, json, traceback
import idaapi, idautils, idc, ida_funcs, ida_bytes, ida_hexrays
idc.Wait()
BASE = idaapi.get_imagebase()
out = []
def w(s):
    out.append(s)
    print(s, flush=True)
try:
    ida_hexrays.init_hexrays_plugin()
    w('imagebase=%#x funcs=%d' % (BASE, ida_funcs.get_func_qty()))
    w('')
    w('=== 1) 搜立即数 6D0h / 6D4h 的使用 (mov [reg+6D0h]) ===')
    pats = ['+6D0h]', '+6D4h]']
    hits = []
    qty = ida_funcs.get_func_qty()
    for i in range(qty):
        f = ida_funcs.getn_func(i)
        if f is None: continue
        if f.end_ea - f.start_ea > 60000: continue
        for item in idautils.FuncItems(f.start_ea):
            d = idc.GetDisasm(item)
            for p in pats:
                if p in d:
                    hits.append((item, d, ida_funcs.get_func_name(f.start_ea)))
    w('  命中 %d 条' % len(hits))
    seen = set()
    for ea, d, fn in hits:
        key = (fn, d.split(',')[0][:40])
        if key in seen: continue
        seen.add(key)
        w('    %#x  %-52s  %s' % (ea, d[:52], fn))
        if len(seen) >= 40: break
    w('')
    w('=== 2) 搜浮点常量 50.0 / 3000.0 的引用 ===')
    for name, val in [('50.0', 50.0), ('3000.0', 3000.0)]:
        found = 0
        for seg_ea in idautils.Segments():
            s = idaapi.getseg(seg_ea)
            if s is None: continue
            if not (s.perm & 1): continue
            ea = s.start_ea
            while ea < s.end_ea:
                b = ida_bytes.get_bytes(ea, 4)
                if b and len(b) == 4:
                    import struct
                    if struct.unpack('<f', b)[0] == val:
                        xr = list(idautils.XrefsTo(ea, 0))
                        if xr:
                            f = ida_funcs.get_func(xr[0].frm)
                            w('    %s @ %#x  被 %d 处引用, 首个 %#x in %s' % (name, ea, len(xr), xr[0].frm, ida_funcs.get_func_name(f.start_ea) if f else '?'))
                            found += 1
                            if found >= 4: break
                ea += 1
            if found >= 4: break
        if found == 0: w('    %s 未找到有引用的位置' % name)
except Exception:
    w('EXC: ' + traceback.format_exc()[:1500])
JF = os.environ.get('LIM_JOB')
if JF:
    cfg = json.load(open(JF, 'r', encoding='utf-8'))
    with open(cfg['output'], 'w', encoding='utf-8') as fh:
        fh.write(chr(10).join(out))
        fh.write(chr(10))
    print('[done] -> ' + cfg['output'], flush=True)
idaapi.qexit(0)
