# -*- coding: utf-8 -*-
# 用 COL 边界判据确定 vftable 的真实槽位数
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
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()

    def col_type(ptr):
        """ptr 若指向合法 COL，返回类名，否则 None"""
        if ptr == 0 or ida_segment.getseg(ptr) is None:
            return None
        if d(ptr) != 1:   # signature
            return None
        td = base + d(ptr + 0x0C)
        if ida_segment.getseg(td) is None:
            return None
        s = rd_str(td + 0x10, 200)
        return s[4:].split('@@')[0] if s.startswith('.?A') else None

    def col_at(vt_ea, back):
        return col_type(q(vt_ea - back))

    all7 = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7'):
            all7.append((ida_name.get_nlist_ea(i), s))
    all7.sort()
    w('total ??_7 = %d' % len(all7))

    # 校验：每个 ??_7 的 -8 处是否是它自己的 COL
    okc = 0
    for ea, s in all7:
        cn = col_at(ea, 8)
        if cn and cn == s[4:].split('@@')[0]:
            okc += 1
    w('COL@-8 与符号名匹配的 vftable: %d / %d' % (okc, len(all7)))

    def true_len(vt_ea, cap=512):
        """用 COL 边界 + 代码段判据求真实槽位数"""
        k = 0
        while k < cap:
            p = q(vt_ea + k * 8)
            seg = ida_segment.getseg(p)
            if p == 0 or seg is None or not (seg.perm & 1):
                break
            # 下一个 8 字节位置若是新 vftable 起点（其 -8 是合法 COL），则当前槽位是最后一位
            if col_type(q(vt_ea + (k + 1) * 8 - 8)) and k > 0:
                k += 1
                break
            k += 1
        return k
    for tgt in ['??_7CEffect@@6B@', '??_7CScriptedEffectTemplate@@6B@', '??_7CPdxMouse@@6B@', '??_7CUnit@@6B@', '??_7CPersistent@@6B@']:
        ea = None
        for a, s in all7:
            if s == tgt:
                ea = a; break
        if ea is None:
            w('MISSING ' + tgt); continue
        L = true_len(ea)
        w('')
        w('##### %s @ 0x%X  真实槽位数=%d' % (tgt, ea, L))
        for k in range(L + 2):
            p = q(ea + k * 8)
            seg = ida_segment.getseg(p)
            code = bool(seg and (seg.perm & 1))
            mark = '  ' if k < L else '>>'
            w('   %s[%2d] 0x%X %-7s %s' % (mark, k, p, 'code' if code else 'NOCODE', ida_name.get_name(p) or '<noname>'))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)