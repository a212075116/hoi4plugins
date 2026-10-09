# -*- coding: utf-8 -*-
# 虚函数命名 v2：按继承深度自顶向下（基类先命名），修正「先到先得」的归属错误
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_nalt
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def q(ea):
    return ida_bytes.get_qword(ea)
def d(ea):
    return ida_bytes.get_dword(ea)
def rd_str(ea, n=200):
    b = ida_bytes.get_bytes(ea, n)
    if not b:
        return ''
    try:
        return b.split(b'\x00')[0].decode('ascii', 'replace')
    except Exception:
        return ''
APPLY = bool(cfg.get('apply', False))
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    before_named = 0
    before_total = 0
    import idautils
    for ea in idautils.Functions():
        before_total += 1
        nm = ida_name.get_name(ea) or ''
        if nm and not nm.startswith('sub_'):
            before_named += 1
    w('BEFORE {"func_qty": %d, "named": %d, "unnamed": %d}'
      % (before_total, before_named, before_total - before_named))
    vt = {}
    r3 = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s:
            continue
        ea = ida_name.get_nlist_ea(i)
        if s.startswith('??_7'):
            vt.setdefault(s[4:].split('@@')[0], []).append((ea, s))
        elif s.startswith('??_R3'):
            r3[s[5:].split('@@')[0]] = ea
    def type_name(dp):
        td = base + d(dp)
        if ida_segment.getseg(td) is None:
            return None
        s = rd_str(td + 0x10, 200)
        return s[4:].split('@@')[0] if s.startswith('.?A') else None
    def bases_of(cls):
        ea = r3.get(cls)
        if ea is None:
            return []
        nb = d(ea + 0x08)
        arr = base + d(ea + 0x0C)
        if nb <= 0 or nb > 64 or ida_segment.getseg(arr) is None:
            return []
        out = []
        for k in range(nb):
            dp = base + d(arr + k * 4)
            if ida_segment.getseg(dp) is None:
                break
            tn = type_name(dp)
            if tn:
                out.append(tn)
        return out[1:] if out else []
    def slots(vt_ea):
        res = []
        for k in range(1024):
            p = q(vt_ea + k * 8)
            seg = ida_segment.getseg(p)
            if p == 0 or seg is None or not (seg.perm & 1):
                break
            res.append(p)
        return res
    depth = {}
    def dep(c, seen=None):
        if c in depth:
            return depth[c]
        if seen is None:
            seen = set()
        if c in seen:
            return 0
        seen.add(c)
        bs = bases_of(c)
        v = 0 if not bs else 1 + max((dep(b, seen) for b in bs), default=0)
        seen.discard(c)
        depth[c] = v
        return v
    for c in vt:
        dep(c)
    order = sorted(vt, key=lambda c: (depth.get(c, 0), c))
    w('vftable classes=%d  depth buckets=%d' % (len(order), len(set(depth.get(c, 0) for c in order))))
    # 短名唯一性（复用既有策略）
    import re
    def flatten(s):
        return re.sub(r'[^A-Za-z0-9_]', '_', s)
    shortcnt = {}
    for c in order:
        sh = c.split('@')[0]
        shortcnt[flatten(sh)] = shortcnt.get(flatten(sh), 0) + 1
    renamed = 0
    skipped = 0
    failed = 0
    used_short = 0
    used_full = 0
    classes_touched = 0
    for cls in order:
        ealist = sorted(vt[cls])
        touched = False
        for vt_ea, sym in ealist:
            suffix = ''
            if sym != ('??_7' + cls + '@@6B@'):
                tail = sym[len('??_7' + cls + '@@6B@'):]
                suffix = '::vtbl' + tail.replace('_', '_')
            fns = slots(vt_ea)
            for k, fn in enumerate(fns):
                cur = ida_name.get_name(fn) or ''
                if cur and not cur.startswith('sub_'):
                    skipped += 1
                    continue
                disp = cls.split('@')[0]
                key = flatten(disp)
                if shortcnt.get(key, 0) == 1:
                    base_nm = disp
                else:
                    base_nm = flatten(cls)
                if not base_nm or base_nm[0].isdigit():
                    base_nm = '_' + base_nm
                nm = '%s%s::vfunc_%d' % (base_nm, suffix, k)
                if shortcnt.get(key, 0) == 1:
                    used_short += 1
                else:
                    used_full += 1
                if not APPLY:
                    renamed += 1
                    touched = True
                    continue
                ok = False
                for attempt in range(0, 9):
                    cand = nm if attempt == 0 else '%s_%d' % (nm, attempt + 1)
                    if ida_name.set_name(fn, cand, ida_name.SN_NOCHECK | ida_name.SN_NOWARN):
                        ok = True
                        break
                if ok:
                    renamed += 1
                    touched = True
                else:
                    failed += 1
        if touched:
            classes_touched += 1
    after_named = 0
    after_total = 0
    if APPLY:
        import idautils as iu
        for ea in iu.Functions():
            after_total += 1
            nm = ida_name.get_name(ea) or ''
            if nm and not nm.startswith('sub_'):
                after_named += 1
    w('apply=%s renamed=%d skipped_already_named=%d setname_failed=%d'
      % (APPLY, renamed, skipped, failed))
    w('used_short=%d used_full=%d classes_touched=%d' % (used_short, used_full, classes_touched))
    if APPLY:
        w('AFTER {"func_qty": %d, "named": %d, "unnamed": %d} delta_named=%+d'
          % (after_total, after_named, after_total - after_named, after_named - before_named))
    else:
        w('DRY-RUN: no changes written')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)