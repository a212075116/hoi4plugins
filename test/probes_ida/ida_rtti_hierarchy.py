# -*- coding: utf-8 -*-
# 从 MSVC RTTI 还原类继承层次（x64：结构内指针为 4 字节 RVA）
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment
import ida_nalt
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
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
    w('imagebase=0x%X' % base)
    # 收集 ??_R3<Class>@@8（ClassHierarchyDescriptor）
    chds = []
    r2s = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s:
            continue
        if s.startswith('??_R3'):
            chds.append((s, ida_name.get_nlist_ea(i)))
        elif s.startswith('??_R2'):
            r2s[s[5:]] = ida_name.get_nlist_ea(i)
    w('??_R3 count=%d  ??_R2 count=%d' % (len(chds), len(r2s)))

    def type_name(desc_ea):
        td_rva = d(desc_ea)
        if td_rva == 0:
            return None
        td = base + td_rva
        if ida_segment.getseg(td) is None:
            return None
        s = rd_str(td + 0x10, 200)
        if s.startswith('.?A'):
            return s[4:].split('@@')[0]
        # 退化：直接读字符串
        return s if s.startswith('.?A') else None

    ok = 0
    bad = 0
    edges = []
    per_class = {}
    for sym, ea in chds:
        cls = sym[5:].split('@@')[0]
        nb = d(ea + 0x08)
        arr_rva = d(ea + 0x0C)
        if arr_rva == 0 or nb == 0 or nb > 64:
            bad += 1
            continue
        arr = base + arr_rva
        if ida_segment.getseg(arr) is None:
            bad += 1
            continue
        names = []
        for k in range(nb):
            dp = base + d(arr + k * 4)
            if ida_segment.getseg(dp) is None:
                break
            tn = type_name(dp)
            if tn is None:
                break
            names.append(tn)
        if not names:
            bad += 1
            continue
        ok += 1
        self_name = names[0]
        bases = names[1:]
        per_class[cls] = bases
        for b in bases:
            if b != cls:
                edges.append((cls, b))
    w('parsed_ok=%d  skipped=%d  classes_with_bases=%d  edges=%d'
      % (ok, bad, sum(1 for v in per_class.values() if v), len(edges)))

    # 统计
    from collections import Counter
    basecnt = Counter(b for _, b in edges)
    w('')
    w('--- 被继承最多的基类 top 25 ---')
    for b, c in basecnt.most_common(25):
        w('  %-52s %d 个子类' % (b, c))
    w('')
    w('--- 继承链样例（含基类的类）---')
    shown = 0
    for cls in sorted(per_class):
        bl = per_class[cls]
        if bl and shown < 40:
            w('  %-46s : %s' % (cls, ', '.join(bl)))
            shown += 1
    w('')
    w('--- 深层继承（基类数 >= 4）---')
    deep = sorted(((c, b) for c, b in per_class.items() if len(b) >= 4), key=lambda x: -len(x[1]))
    w('count=%d' % len(deep))
    for c, b in deep[:25]:
        w('  [%d] %s : %s' % (len(b), c, ', '.join(b)))
    json.dump({'per_class': per_class, 'edges': edges}, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False)
    w('')
    w('json written: ' + cfg['json'])
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)