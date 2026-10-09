# -*- coding: utf-8 -*-
# vftable -> <Class>::vfunc_N 批量命名（混合策略）
# 短名（模板参数截断）唯一时用短名，否则回退到完整名以保证可区分
import os, json, re, traceback, collections
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment, ida_funcs

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
APPLY = bool(cfg.get('apply', False))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
AUTO = ('sub_', 'loc_', 'byte_', 'word_', 'dword_', 'qword_', 'unk_', 'off_', 'nullsub_', 'unknown_', 'j_sub_', 'j_')
def is_auto(nm):
    return (not nm) or nm.startswith(AUTO)
VT_RE = re.compile(r'^\?\?_7(.+)@6B@(_\d+)?$')
DEM_RE = re.compile(r'^(?:const |volatile )*(.+?)::`vftable\'$')
FLAT_RE = re.compile(r'[^A-Za-z0-9_$?:@.]')
def flatten(s):
    return FLAT_RE.sub('_', s)
def clean(raw, dup):
    cls = raw.replace("`anonymous namespace'", 'anon_ns')
    cls = cls.replace('`', '_').replace("'", '_').replace('"', '_')
    cls = cls.replace(' ', '_').strip(':')
    if dup:
        cls = cls + '::vtbl' + dup
    return cls
def variants(sym, dup):
    try:
        d = ida_name.demangle_name(sym, ida_name.MNG_SHORT_FORM)
    except Exception:
        d = None
    if not d:
        return None, None, 'demangle_none'
    m = DEM_RE.match(d)
    if not m:
        return None, None, 'dem_re_fail'
    raw = m.group(1).strip()
    full = clean(raw, dup)
    i = raw.find('<')
    short = clean(raw[:i] if i > 0 else raw, dup)
    if not full or not short:
        return None, None, 'empty_cls'
    return full, short, None
def snapshot():
    qty = ida_funcs.get_func_qty()
    unnamed = 0
    for i in range(qty):
        fn = ida_funcs.getn_func(i)
        if fn is None:
            continue
        nm = ida_funcs.get_func_name(fn.start_ea)
        if not nm or nm.startswith(('sub_', 'unknown_', 'nullsub_', 'j_sub_')):
            unnamed += 1
    return {'func_qty': qty, 'unnamed': unnamed, 'named': qty - unnamed}
try:
    ida_auto.auto_wait()
    before = snapshot()
    w('BEFORE %s' % json.dumps(before))
    n = ida_name.get_nlist_size()
    vt = []
    for i in range(n):
        nm = ida_name.get_nlist_name(i)
        if nm and nm.startswith('??_7'):
            vt.append((nm, ida_name.get_nlist_ea(i)))
    vt.sort(key=lambda x: x[1])
    entries = []
    short_use = collections.Counter()
    reasons = {}
    for sym, ea in vt:
        m = VT_RE.match(sym)
        dup = m.group(2) if m else None
        full, short, why = variants(sym, dup)
        if not full:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        entries.append((sym, ea, full, short))
        short_use[flatten(short)] += 1
    w('vftables=%d parsed=%d unparsed=%d' % (len(vt), len(entries), len(vt) - len(entries)))
    w('parse_reasons=%s' % json.dumps(reasons))
    w('distinct_short_names=%d  short_names_colliding=%d'
      % (len(short_use), sum(1 for v in short_use.values() if v > 1)))
    renamed = skipped = failed = used_short = used_full = 0
    per_class = []
    samples = []
    for idx in range(len(entries)):
        sym, ea, full, short = entries[idx]
        cls = short if short_use[flatten(short)] == 1 else full
        end = entries[idx + 1][1] if idx + 1 < len(entries) else ea + 64 * 8
        if end <= ea:
            end = ea + 64 * 8
        cur = ea; slot = 0; done = 0
        while cur + 8 <= end and slot < 64:
            tgt = ida_bytes.get_qword(cur)
            if tgt == 0 or tgt == 0xFFFFFFFFFFFFFFFF:
                break
            seg = ida_segment.getseg(tgt)
            if seg is None or not ida_bytes.is_loaded(tgt) or not (seg.perm & 1):
                break
            if not is_auto(ida_name.get_name(tgt)):
                skipped += 1
            else:
                base = '%s::vfunc_%d' % (cls, slot)
                ok = True
                if APPLY:
                    ok = bool(ida_name.set_name(tgt, base, ida_name.SN_NOCHECK | ida_name.SN_NOWARN))
                    if not ok:
                        for k in range(2, 9):
                            alt = '%s_%d' % (base, k)
                            if ida_name.set_name(tgt, alt, ida_name.SN_NOCHECK | ida_name.SN_NOWARN):
                                ok = True; base = alt; break
                if ok:
                    renamed += 1; done += 1
                    if cls == short:
                        used_short += 1
                    else:
                        used_full += 1
                    if len(samples) < 18:
                        samples.append('%-46s +%-2d -> %s' % (sym[:46], slot, base[:80]))
                else:
                    failed += 1
            slot += 1
            cur += 8
        if done:
            per_class.append((cls, done))
    w('renamed=%d skipped_already_named=%d setname_failed=%d' % (renamed, skipped, failed))
    w('used_short_name=%d used_full_name=%d classes_touched=%d' % (used_short, used_full, len(per_class)))
    if APPLY:
        after = snapshot()
        w('AFTER  %s' % json.dumps(after))
        w('delta_named=+%d' % (after['named'] - before['named']))
    w('\n--- sample renames ---')
    for s in samples:
        w('  ' + s)
    w('\n--- top 15 classes ---')
    for c, k in sorted(per_class, key=lambda x: -x[1])[:15]:
        w('  %-56s %d' % (c[:56], k))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)