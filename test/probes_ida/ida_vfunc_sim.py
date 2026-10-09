# -*- coding: utf-8 -*-
# 只读模拟：按继承深度自顶向下命名，能否修正归属
import os, json, traceback, collections
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
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    vt = {}
    r3 = {}
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
    # 模拟两种顺序的命名归属
    def simulate(order):
        owner = {}
        for cls in order:
            for fn in slots(vt[cls][0]):
                if fn not in owner:
                    owner[fn] = cls
        return owner
    naive_order = sorted(vt)
    depth_order = sorted(vt, key=lambda c: (depth.get(c, 0), c))
    res = {}
    for tag, order in (('旧的字母序', naive_order), ('新的继承深度序', depth_order)):
        owner = simulate(order)
        cmp_ = 0; inh = 0; okb = 0; badb = 0
        for cls in sorted(vt):
            bs = bases_of(cls)
            if not bs:
                continue
            b0 = bs[0]
            if b0 not in vt:
                continue
            sc = slots(vt[cls][0]); sb = slots(vt[b0][0])
            m = min(len(sc), len(sb))
            for k in range(m):
                cmp_ += 1
                if sc[k] == sb[k]:
                    inh += 1
                    o = owner.get(sc[k], '')
                    if o == b0 or o in bases_of(b0) or o == cls:
                        okb += 1
                    else:
                        badb += 1
        res[tag] = (cmp_, inh, okb, badb)
        w('%s: 槽位对比=%d 继承槽位=%d' % (tag, cmp_, inh))
        if inh:
            w('    归属基类/自身=%d (%.1f%%)   归属无关类=%d (%.1f%%)'
              % (okb, 100.0 * okb / inh, badb, 100.0 * badb / inh))
    w('')
    w('深度分布: ' + ', '.join('%d:%d' % (k, v) for k, v in sorted(collections.Counter(depth.values()).items())))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)