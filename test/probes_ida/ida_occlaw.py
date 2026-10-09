import os, sys, json, traceback
import idaapi, idautils, idc, ida_funcs, ida_hexrays, ida_auto, ida_bytes, ida_name
ida_auto.auto_wait()
out = []
def w(s):
    out.append(str(s)); print(s, flush=True)
def flush():
    JF = os.environ.get('GJOB')
    if JF:
        cfg = json.load(open(JF, 'r', encoding='utf-8'))
        open(cfg['output'], 'w', encoding='utf-8').write(chr(10).join(out) + chr(10))
try:
    ida_hexrays.init_hexrays_plugin()
    w('imagebase=%#x' % idaapi.get_imagebase())
    seen = []
    w('')
    w('=== 目标字符串 ===')
    for s in idautils.Strings():
        v = str(s)
        if 'GetOccupationLaw' in v or 'occupatin' in v or 'occupation is not initialzied' in v:
            seen.append((s.ea, v))
            w('  ea=%#x  %r' % (s.ea, v))
    w('')
    w('=== 引用与所在函数 ===')
    funcs = []
    for ea, v in seen:
        for x in idautils.XrefsTo(ea, 0):
            f = ida_funcs.get_func(x.frm)
            nm = ida_funcs.get_func_name(f.start_ea) if f else '?'
            w('  %r <- %#x in %s' % (v[:40], x.frm, nm))
            if f and f.start_ea not in [t[0] for t in funcs]:
                funcs.append((f.start_ea, nm))
    w('')
    for fe, nm in funcs[:4]:
        f = ida_funcs.get_func(fe)
        w('=== %s  (%#x, %d bytes) ===' % (nm, fe, f.end_ea - fe))
        try:
            cf = ida_hexrays.decompile(fe)
            if cf:
                for l in str(cf).split(chr(10))[:130]: w('  ' + l)
        except Exception as e:
            w('  反编译失败: %s' % e)
        w('')
except Exception:
    w('EXC: ' + traceback.format_exc()[:1500])
flush()
idaapi.qexit(0)
