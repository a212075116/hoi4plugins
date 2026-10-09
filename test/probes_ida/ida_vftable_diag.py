# -*- coding: utf-8 -*-
# 只读诊断：vftable 槽位指向的函数是否已有符号名
import os, json, collections, traceback
import ida_funcs, ida_pro, ida_auto, ida_name, ida_bytes, ida_segment

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
AUTO = ('sub_', 'loc_', 'byte_', 'word_', 'dword_', 'qword_', 'unk_', 'off_', 'nullsub_', 'unknown_')
def is_auto(nm):
    return (not nm) or nm.startswith(AUTO)

try:
    ida_auto.auto_wait()
    n = ida_name.get_nlist_size()
    vt = []
    for i in range(n):
        nm = ida_name.get_nlist_name(i)
        if nm and nm.startswith('??_7'):
            vt.append((nm, ida_name.get_nlist_ea(i)))
    vt.sort(key=lambda x: x[1])
    w('vftable_symbols=%d' % len(vt))
    total = named = auto = 0
    all_named = partial = all_auto = empty = 0
    samp_auto = []
    samp_part = []
    for idx in range(len(vt)):
        nm, ea = vt[idx]
        end = vt[idx + 1][1] if idx + 1 < len(vt) else ea + 64 * 8
        if end <= ea:
            end = ea + 64 * 8
        cnt = 0; a = 0; nmd = 0
        cur = ea
        while cur + 8 <= end and cnt < 64:
            tgt = ida_bytes.get_qword(cur)
            if tgt == 0 or tgt == 0xFFFFFFFFFFFFFFFF:
                break
            seg = ida_segment.getseg(tgt)
            if seg is None or not ida_bytes.is_loaded(tgt) or not (seg.perm & 1):
                break
            if is_auto(ida_name.get_name(tgt)):
                a += 1
            else:
                nmd += 1
            cnt += 1; cur += 8
        if cnt == 0:
            empty += 1
            continue
        total += cnt; named += nmd; auto += a
        if a == 0:
            all_named += 1
        elif nmd == 0:
            all_auto += 1
            if len(samp_auto) < 12: samp_auto.append((nm, cnt))
        else:
            partial += 1
            if len(samp_part) < 12: samp_part.append((nm, nmd, a))
    w('vftables_with_slots=%d  (empty=%d)' % (all_named + partial + all_auto, empty))
    w('  all_slots_named   = %d' % all_named)
    w('  partial           = %d' % partial)
    w('  all_slots_unnamed = %d' % all_auto)
    w('slots: total=%d named=%d unnamed=%d  named%%=%.1f' % (total, named, auto, 100.0 * named / max(1, total)))
    w('\n--- fully unnamed vftables (sample) ---')
    for nm, c in samp_auto:
        w('  %-64s slots=%d' % (nm, c))
    w('\n--- partially named vftables (sample) ---')
    for nm, a2, b2 in samp_part:
        w('  %-64s named=%d unnamed=%d' % (nm, a2, b2))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)