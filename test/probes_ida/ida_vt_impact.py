# -*- coding: utf-8 -*-
# 影响分析：原命名脚本的越界读取规模（用 COL 边界判据对比）
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
        if ptr == 0 or ida_segment.getseg(ptr) is None:
            return None
        if d(ptr) != 1:
            return None
        td = base + d(ptr + 0x0C)
        if ida_segment.getseg(td) is None:
            return None
        s = rd_str(td + 0x10, 200)
        return s[4:].split('@@')[0] if s.startswith('.?A') else None

    def naive_len(vt, cap=1024):
        k = 0
        while k < cap:
            p = q(vt + k * 8)
            seg = ida_segment.getseg(p)
            if p == 0 or seg is None or not (seg.perm & 1):
                break
            k += 1
        return k

    def col_len(vt, cap=1024):
        k = 0
        while k < cap:
            p = q(vt + k * 8)
            seg = ida_segment.getseg(p)
            if p == 0 or seg is None or not (seg.perm & 1):
                break
            if k > 0 and col_type(q(vt + (k + 1) * 8 - 8)) is not None:
                k += 1
                break
            k += 1
        return k

    all7 = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7'):
            all7.append((ida_name.get_nlist_ea(i), s))
    all7.sort()
    tot_naive = 0
    tot_col = 0
    overshoot_tables = 0
    overshoot_slots = 0
    capped = 0
    for ea, s in all7:
        a = naive_len(ea)
        b = col_len(ea)
        tot_naive += a
        tot_col += b
        if a >= 1024:
            capped += 1
        if a > b:
            overshoot_tables += 1
            overshoot_slots += (a - b)
    w('vftable 总数 = %d' % len(all7))
    w('旧法(连续读到非代码)总槽位 = %d' % tot_naive)
    w('新法(COL 边界)    总槽位 = %d' % tot_col)
    w('旧法读到 1024 上限的表 = %d' % capped)
    w('旧法越界的表 = %d (%.1f%%)' % (overshoot_tables, 100.0 * overshoot_tables / len(all7)))
    w('旧法多读的槽位总数 = %d' % overshoot_slots)
    w('')
    w('说明：旧法多读的槽位若指向无名函数，就会被错误命名')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)