# -*- coding: utf-8 -*-
# 诊断：IDA 自己对 vftable 的标注（类型/长度/名称），据此确定正确的槽位数
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_nalt, ida_ua, ida_xref
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def q(ea):
    return ida_bytes.get_qword(ea)
def d(ea):
    return ida_bytes.get_dword(ea)
def try_(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        return 'ERR:%s' % e
try:
    ida_auto.auto_wait()
    # 收集所有 ??_7 符号地址并排序，用于估计相邻边界
    all7 = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7'):
            all7.append((ida_name.get_nlist_ea(i), s))
    all7.sort()
    w('total ??_7 = %d' % len(all7))
    addr_set = dict(all7)
    for tgt_sym in ['??_7CEffect@@6B@', '??_7CScriptedEffectTemplate@@6B@', '??_7?$CAddMilitaryRoleEffect@$00@@6B@', '??_7CPdxMouse@@6B@']:
        ea = None
        for a, s in all7:
            if s == tgt_sym:
                ea = a; break
        if ea is None:
            w('MISSING %s' % tgt_sym); continue
        w('')
        w('##### %s @ 0x%X' % (tgt_sym, ea))
        w('  get_item_size   = %s' % try_(ida_bytes.get_item_size, ea))
        w('  get_item_head   = 0x%X' % (try_(ida_bytes.get_item_head, ea) if not isinstance(try_(ida_bytes.get_item_head, ea), str) else 0))
        w('  get_item_end    = 0x%X' % (try_(ida_bytes.get_item_end, ea) if not isinstance(try_(ida_bytes.get_item_end, ea), str) else 0))
        w('  get_flags       = 0x%X' % try_(ida_bytes.get_flags, ea))
        w('  is_data/is_code = %s / %s' % (try_(ida_bytes.is_data, ea), try_(ida_bytes.is_code, ea)))
        w('  has_name        = %s' % try_(ida_bytes.has_name, ida_bytes.get_flags(ea)))
        w('  nalt.get_aflags = %s' % try_(ida_nalt.get_aflags, ea))
        # 用 type 打印（ida_bytes.print_item / 或 calc_type）
        w('  guess_tinfo     = %s' % try_(ida_nalt.get_tinfo, ea))
        # 与下一个 ??_7 的距离
        nxt = None
        for a, s in all7:
            if a > ea:
                nxt = (a, s); break
        if nxt:
            w('  next ??_7 @ 0x%X (%s) 距离=0x%X (%d 字节, 约 %d 槽)' % (nxt[0], nxt[1], nxt[0] - ea, nxt[0] - ea, (nxt[0] - ea) // 8))
        # 数据交叉引用：谁引用了这个地址
        xr = []
        for x in ida_xref.xrefs_from(ea):
            xr.append('%s->0x%X' % (try_(ida_xref.xrefchar, x.type), x.to))
        w('  xrefs_from      = %s' % (', '.join(xr[:6]) if xr else 'none'))
        # 逐槽位，标出哪些槽位落在 `下一个 ??_7` 范围之外/之内
        w('  slots (前 24 个，标注是否在名表/是否 code):')
        for k in range(24):
            p = q(ea + k * 8)
            seg = ida_segment.getseg(p)
            code = bool(seg and (seg.perm & 1))
            nm = ida_name.get_name(p) or ''
            flag = 'code' if code else 'NOTCODE'
            w('     [%2d] 0x%X %-8s %s' % (k, p, flag, nm))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)