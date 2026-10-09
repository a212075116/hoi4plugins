# -*- coding: utf-8 -*-
# 审计：用继承层次检验「先到先得」的虚函数命名是否准确
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_funcs, ida_nalt
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
    # 1) vftable 地址 -> 类名
    vt = {}
    r3 = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s:
            continue
        ea = ida_name.get_nlist_ea(i)
        if s.startswith('??_7'):
            cls = s[4:].split('@@')[0]
            vt.setdefault(cls, []).append(ea)
        elif s.startswith('??_R3'):
            r3[s[5:].split('@@')[0]] = ea
    w('vftable classes=%d  total vftables=%d' % (len(vt), sum(len(v) for v in vt.values())))

    def type_name(desc_ea):
        td = base + d(desc_ea)
        if ida_segment.getseg(td) is None:
            return None
        s = rd_str(td + 0x10, 200)
        return s[4:].split('@@')[0] if s.startswith('.?A') else None

    # 2) 类 -> 直接基类列表（按 RTTI 顺序）
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

    # 3) 读 vftable 槽位 -> 函数地址列表（读到非 .text 或 0 为止）
    def slots(vt_ea):
        res = []
        for k in range(400):
            p = q(vt_ea + k * 8)
            if p == 0:
                break
            seg = ida_segment.getseg(p)
            if seg is None or not (seg.perm & 1):
                break
            res.append(p)
        return res

    def nm(ea):
        s = ida_name.get_name(ea)
        return s or ''

    # 4) 审计：对每个类与其第 0 个基类比较槽位
    stat = {'cmp': 0, 'inherit': 0, 'override': 0, 'name_ok': 0, 'name_bad': 0, 'bad_examples': []}
    checked = 0
    for cls in sorted(vt):
        bs = bases_of(cls)
        if not bs:
            continue
        b0 = bs[0]
        if b0 not in vt or cls not in vt:
            continue
        sc = slots(vt[cls][0])
        sb = slots(vt[b0][0])
        m = min(len(sc), len(sb))
        checked += 1
        for k in range(m):
            stat['cmp'] += 1
            if sc[k] == sb[k]:
                stat['inherit'] += 1
                cur = nm(sc[k])
                want_prefix = b0 + '::'
                if cur.startswith(want_prefix) or (b0.split('@')[0] in cur and b0 in cur):
                    stat['name_ok'] += 1
                else:
                    stat['name_bad'] += 1
                    if len(stat['bad_examples']) < 15:
                        stat['bad_examples'].append('%s slot%d -> %s (基类=%s)' % (cls, k, cur, b0))
            else:
                stat['override'] += 1
    w('')
    w('对比的类=%d  槽位对比=%d' % (checked, stat['cmp']))
    w('  继承槽位(指向基类同一函数)=%d' % stat['inherit'])
    w('  重写槽位(指向不同函数)=%d' % stat['override'])
    if stat['inherit']:
        pct = 100.0 * stat['name_ok'] / stat['inherit']
        w('  继承槽位中，名字已归属基类的=%d (%.1f%%)，仍挂在派生类下的=%d'
          % (stat['name_ok'], pct, stat['name_bad']))
    w('')
    w('--- 名字归属可疑样例 ---')
    for e in stat['bad_examples']:
        w('  ' + e)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)