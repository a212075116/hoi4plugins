import os, sys, json, traceback
import idaapi, idautils, idc, ida_funcs, ida_hexrays, ida_auto
ida_auto.auto_wait()
BASE = idaapi.get_imagebase()
out = []
def w(s):
    out.append(s); print(s, flush=True)
try:
    ida_hexrays.init_hexrays_plugin()
    w('imagebase=%#x' % BASE)
    w('')
    w('=== crashdir 字符串及其引用 ===')
    tgt = []
    for s in idautils.Strings():
        v = str(s)
        if 'crashdir' in v or 'crash_reporter_dir' in v:
            tgt.append((s.ea, v))
            w('  str %#x  %r' % (s.ea, v))
    w('')
    funcs = []
    for ea, v in tgt:
        for x in idautils.XrefsTo(ea, 0):
            f = ida_funcs.get_func(x.frm)
            nm = ida_funcs.get_func_name(f.start_ea) if f else '?'
            w('  %r <- %#x in %s' % (v[:28], x.frm, nm))
            if f and f.start_ea not in [t[0] for t in funcs]:
                funcs.append((f.start_ea, nm))
    w('')
    for fe, nm in funcs[:3]:
        f = ida_funcs.get_func(fe)
        w('=== decompile %s (%#x, %d bytes) ===' % (nm, fe, f.end_ea - fe))
        try:
            cf = ida_hexrays.decompile(fe)
            if cf:
                for l in str(cf).split(chr(10))[:100]: w('  ' + l)
        except Exception as e:
            w('  失败: %s' % e)
        w('')
except Exception:
    w('EXC: ' + traceback.format_exc()[:1200])
JF = os.environ.get('CD_JOB')
if JF:
    cfg = json.load(open(JF, 'r', encoding='utf-8'))
    open(cfg['output'], 'w', encoding='utf-8').write(chr(10).join(out) + chr(10))
    print('[done]', flush=True)
idaapi.qexit(0)
