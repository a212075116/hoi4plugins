# -*- coding: utf-8 -*-
# 验证：继承深度序命名后的归属准确率 + 名字质量
import os, json, traceback, collections, re
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_nalt, idautils
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
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    tot = 0; named = 0
    for ea in idautils.Functions():
        tot += 1
        nm = ida_name.get_name(ea) or ''
        if nm and not nm.startswith('sub_'):
            named += 1
    w('TOTAL {"func_qty": %d, "named": %d, "unnamed": %d, "pct": %.1f}'
      % (tot, named, tot - named, 100.0 * named / max(1, tot)))

    vt = {}; r3 = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s:
            continue
        ea = ida_name.get_nlist_ea(i)
        if s.startswith('??_7'):
            vt.setdefault(s[4:].split('@@')[0], []).append(ea)
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
        nb = d(ea + 0x08); arr = base + d(ea + 0x0C)
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

    def flat(s):
        return re.sub(r'[^A-Za-z0-9_]', '_', s)

    # 归属准确率
    cmp_ = 0; inh = 0; okb = 0; badb = 0; own = 0
    bad_ex = []
    for cls in sorted(vt):
        bs = bases_of(cls)
        if not bs or bs[0] not in vt:
            continue
        b0 = bs[0]
        sc = slots(vt[cls][0]); sb = slots(vt[b0][0])
        for k in range(min(len(sc), len(sb))):
            cmp_ += 1
            if sc[k] != sb[k]:
                continue
            inh += 1
            cur = ida_name.get_name(sc[k]) or ''
            owner = cur.split('::')[0] if '::' in cur else cur
            cand = set([b0, cls]) | set(bases_of(b0))
            if owner in cand or flat(owner) == flat(b0) or flat(owner) == flat(cls):
                okb += 1
            else:
                badb += 1
                if len(bad_ex) < 12:
                    bad_ex.append('%s slot%d -> %s (基类=%s)' % (cls, k, cur, b0))
    w('')
    w('归属审计: 槽位对比=%d 继承槽位=%d' % (cmp_, inh))
    if inh:
        w('  归属基类/自身 = %d (%.1f%%)' % (okb, 100.0 * okb / inh))
        w('  其他          = %d (%.1f%%)' % (badb, 100.0 * badb / inh))

    # 名字质量
    clean = 0; ugly = 0; vf = 0; hist = collections.Counter()
    for ea in idautils.Functions():
        nm = ida_name.get_name(ea) or ''
        if '::vfunc_' not in nm:
            continue
        vf += 1
        cls = nm.split('::vfunc_')[0]
        L = len(cls)
        if L <= 30:
            hist['<=30'] += 1
        elif L <= 60:
            hist['31-60'] += 1
        elif L <= 100:
            hist['61-100'] += 1
        else:
            hist['>100'] += 1
        if L <= 60 and '(' not in cls and ')' not in cls:
            clean += 1
        else:
            ugly += 1
    w('')
    w('vfunc 命名总数=%d  clean=%d (%.1f%%)  ugly=%d (%.1f%%)'
      % (vf, clean, 100.0 * clean / max(1, vf), ugly, 100.0 * ugly / max(1, vf)))
    w('长度分布: ' + json.dumps(dict(hist)))
    w('')
    w('--- 归属可疑样例 ---')
    for e in bad_ex:
        w('  ' + e)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)