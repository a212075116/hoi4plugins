# -*- coding: utf-8 -*-
# 核对 CUnit 虚表：符号地址、槽位边界、是否有重复项
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_funcs, ida_nalt
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    # 1) IDA 中所有 CUnit 的 vftable 符号
    w('=== 含 CUnit 的 ??_7 符号 ===')
    n = ida_name.get_nlist_size()
    syms = []
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7') and 'CUnit' in s:
            ea = ida_name.get_nlist_ea(i)
            syms.append((ea, s))
            w('  0x%-12X  %s' % (ea, s))
    w('')
    # 2) 对每个符号，向前向后看边界
    for ea, s in syms:
        w('##### 符号 0x%X  %s' % (ea, s))
        seg = ida_segment.getseg(ea)
        w('  段 = %s' % (ida_segment.get_segm_name(seg) if seg else '<none>'))
        # 先确认 -8 是不是 COL
        col = ida_bytes.get_qword(ea - 8)
        w('  [ea-8] = 0x%X  %s' % (col, ida_name.get_name(col) or ''))
        # 向后扫，遇到非代码指针或重复项就报告
        w('  槽位扫描(前 30):')
        seen = {}
        lastgood = 0
        for k in range(30):
            v = ida_bytes.get_qword(ea + k * 8)
            seg2 = ida_segment.getseg(v)
            code = bool(seg2 and (seg2.perm & 1))
            nm = ida_name.get_name(v) or ''
            mark = ''
            if not code:
                mark = '  <<< 非代码，边界'
            if v in seen:
                mark += '  <<< 与槽位 %d 重复!' % seen[v]
            else:
                seen[v] = k
            w('    [%2d] 0x%-12X %-5s %-46s%s' % (k, v, 'code' if code else 'NO', nm[:46], mark))
            if code:
                lastgood = k
        w('  -> 连续代码槽位到 [%d]，共 %d 个' % (lastgood, lastgood + 1))
        w('')
    # 3) vt_list.json 里 CUnit 的记录
    vt = json.load(open(cfg['vt_in'], encoding='utf-8'))['vt']
    w('=== vt_list.json 中 CUnit 的记录 ===')
    for x in vt:
        if x['cls'] == 'CUnit':
            w('  sym=%s ea=0x%X rva=0x%X n=%d' % (x['sym'], x['ea'], x['rva'], x['n']))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)