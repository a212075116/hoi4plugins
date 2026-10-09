# -*- coding: utf-8 -*-
# 诊断：某个类的所有 vftable 符号及其真实槽位内容
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_nalt
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def d(ea):
    return ida_bytes.get_dword(ea)
def q(ea):
    return ida_bytes.get_qword(ea)
def rd_str(ea, n=200):
    b = ida_bytes.get_bytes(ea, n)
    if not b:
        return ''
    try:
        return b.split(b'\x00')[0].decode('ascii', 'replace')
    except Exception:
        return ''
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    targets = ['?$CAddMilitaryRoleEffect@$00', 'CEffect', 'CScriptedEffectTemplate']
    all7 = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7'):
            all7.setdefault(s[4:].split('@@')[0], []).append((s, ida_name.get_nlist_ea(i)))
    for t in targets:
        w('')
        w('##### %s -> %d 个 ??_7 符号' % (t, len(all7.get(t, []))))
        for sym, ea in all7.get(t, [])[:4]:
            w('  %s @ 0x%X' % (sym, ea))
            # COL 在虚表之前
            for back in (8, 16, 24, 32):
                cand = ea - back
                col = q(cand)
                if col and ida_segment.getseg(col):
                    sig = d(col)
                    off = d(col + 4)
                    td = base + d(col + 0x0C)
                    nm = rd_str(td + 0x10, 120) if ida_segment.getseg(td) else ''
                    if nm.startswith('.?A'):
                        w('    COL @-0x%X: sig=%d offset=%d type=%s' % (back, sig, off, nm[4:].split('@@')[0]))
            for k in range(22):
                p = q(ea + k * 8)
                if p == 0:
                    w('    slot %-2d = 0x0 (end)' % k)
                    break
                seg = ida_segment.getseg(p)
                if seg is None or not (seg.perm & 1):
                    w('    slot %-2d = 0x%X (non-code, stop)' % (k, p))
                    break
                w('    slot %-2d = 0x%X  %s' % (k, p, ida_name.get_name(p) or '<noname>'))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)