# -*- coding: utf-8 -*-
# 只读探查：MSVC x64 RTTI 结构在数据库中的真实布局（API 探测式）
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_idaapi
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def q(ea):
    return ida_bytes.get_qword(ea)
def d(ea):
    return ida_bytes.get_dword(ea)
def find_api(mods, anames):
    import importlib
    for mn in mods:
        try:
            m = importlib.import_module(mn)
        except Exception:
            continue
        for an in anames:
            fn = getattr(m, an, None)
            if fn is not None:
                return mn + '.' + an, fn
    return None, None
def rd_str(ea, n=200):
    b = ida_bytes.get_bytes(ea, n)
    if not b:
        return ''
    s = b.split(b'\x00')[0]
    try:
        return s.decode('ascii', 'replace')
    except Exception:
        return repr(s)
try:
    ida_auto.auto_wait()
    nm, fn = find_api(['ida_nalt', 'ida_ida', 'ida_idaapi'], ['get_imagebase'])
    w('imagebase api = %s' % nm)
    if fn:
        w('imagebase = 0x%X' % fn())
    cands = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_R3') and len(cands) < 3:
            cands.append((s, ida_name.get_nlist_ea(i)))
    w('found %d ??_R3 candidates' % len(cands))
    for s, ea in cands:
        w('')
        w('===== %s @ 0x%X =====' % (s, ea))
        w('  CHD: sig=0x%X attr=0x%X numBase=%d pBaseArray=0x%X'
          % (d(ea), d(ea + 4), d(ea + 8), q(ea + 0x10)))
        pa = q(ea + 0x10)
        seg = ida_segment.getseg(pa)
        if seg is None:
            w('  pBaseClassArray 0x%X not mapped' % pa)
            continue
        w('  array in seg %s' % ida_segment.get_segm_name(seg))
        nb = d(ea + 8)
        for k in range(min(6, nb)):
            dp = q(pa + k * 8)
            s2 = ida_segment.getseg(dp)
            line = '    [%d] desc=0x%X' % (k, dp)
            if s2:
                td = q(dp)
                if ida_segment.getseg(td):
                    line += ' typeDesc=0x%X name=%s' % (td, rd_str(td + 0x10, 160))
                line += ' | numCont=%d mdisp=%d pdisp=%d vdisp=%d attr=0x%X pCHD=0x%X'
                line = line % (d(dp + 8), d(dp + 0xC), d(dp + 0x10), d(dp + 0x14), d(dp + 0x18), q(dp + 0x20))
            else:
                line += ' <not mapped>'
            w(line)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)