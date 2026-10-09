# -*- coding: utf-8 -*-
# L1 导出：每个类的虚函数列表 + IDA 已有签名（不反编译，快）
import os, json, traceback, collections
import ida_pro, ida_auto, ida_name, ida_funcs, ida_nalt, ida_typeinf, ida_bytes, ida_segment
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    vt = json.load(open(cfg['vt_in'], encoding='utf-8'))['vt']
    base = ida_nalt.get_imagebase()
    w('vftables = %d' % len(vt))
    LIMIT = int(cfg.get('limit', 400))
    out = []
    known_sig = 0
    unknown_sig = 0
    nofunc = 0
    for idx, x in enumerate(vt[:LIMIT]):
        ea = base + x['rva']
        entry = {'cls': x['cls'], 'rva': x['rva'], 'n': x['n'], 'funcs': []}
        for k in range(x['n']):
            p = ida_bytes.get_qword(ea + k * 8)
            if p == 0:
                entry['funcs'].append({'slot': k, 'ea': 0, 'name': None, 'sig': None})
                continue
            seg = ida_segment.getseg(p)
            iscode = bool(seg and (seg.perm & 1))
            nm = ida_name.get_name(p) or None
            ti = ida_typeinf.tinfo_t()
            sig = None
            if ida_nalt.get_tinfo(ti, p):
                sig = ti.dstr()
            if p and iscode:
                if ida_funcs.get_func(p):
                    if sig and 'fastcall(__int64)' not in sig:
                        known_sig += 1
                    else:
                        unknown_sig += 1
                else:
                    nofunc += 1
            entry['funcs'].append({'slot': k, 'ea': p, 'code': iscode, 'name': nm, 'sig': sig})
        out.append(entry)
        if idx % 500 == 0:
            w('  ...%d/%d' % (idx, min(LIMIT, len(vt))))
    w('')
    w('已识别签名 = %d' % known_sig)
    w('未识别签名(__int64 __fastcall(__int64)) = %d' % unknown_sig)
    w('有函数头但无签名 = %d' % nofunc)
    json.dump(out, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False)
    # 示例输出
    w('')
    w('=== 示例：前 3 个类的虚函数 ===')
    for e in out[:3]:
        w('class %s  (slots=%d)' % (e['cls'], e['n']))
        for fn in e['funcs'][:8]:
            w('    [%2d] %-16s %-46s %s' % (fn['slot'], hex(fn['ea']) if fn['ea'] else '0',
              (fn['name'] or '')[:46], (fn['sig'] or '')[:60]))
        w('')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)