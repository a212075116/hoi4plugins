# -*- coding: utf-8 -*-
# 从构造函数提取类布局（修正：剥离 IDA 颜色标记）
import os, json, traceback, collections, re
import ida_pro, ida_auto, ida_name, ida_funcs, ida_bytes, ida_lines, idautils, ida_idaapi, ida_nalt
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def dis(ea):
    return ida_lines.tag_remove(ida_lines.generate_disasm_line(ea, 0) or '')
RE_MOV = re.compile(r'^mov\s+\[([a-z0-9]+)(?:\+([0-9A-Fa-f]+)h)?\]\s*,\s*([a-z0-9]+)$')
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    LIMIT = int(cfg.get('limit', 400))
    vt = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and s.startswith('??_7'):
            vt[ida_name.get_nlist_ea(i)] = s
    w('vftable syms = %d' % len(vt))
    fn2refs = collections.defaultdict(list)
    for ea, sym in vt.items():
        for r in idautils.DataRefsTo(ea):
            fn = ida_funcs.get_func(r)
            if fn:
                fn2refs[fn.start_ea].append((r, sym))
    w('引用虚表的函数数 = %d' % len(fn2refs))
    layouts = []
    done = 0
    for fn_ea in fn2refs:
        if done >= LIMIT:
            break
        done += 1
        fn = ida_funcs.get_func(fn_ea)
        if not fn:
            continue
        pat = []
        ea = fn.start_ea
        while ea < fn.end_ea:
            nm = None
            for r in idautils.DataRefsFrom(ea):
                t = ida_name.get_name(r) or ''
                if t.startswith('??_7'):
                    nm = t
                    break
            if nm:
                nxt = ida_bytes.next_head(ea, fn.end_ea)
                if nxt != ida_idaapi.BADADDR and nxt > ea:
                    m = RE_MOV.match(dis(nxt).strip())
                    if m:
                        off = int(m.group(2), 16) if m.group(2) else 0
                        pat.append((nm, m.group(1), off, nxt))
            nxt = ida_bytes.next_head(ea, fn.end_ea)
            if nxt == ida_idaapi.BADADDR or nxt <= ea:
                break
            ea = nxt
        if pat:
            layouts.append({'fn': fn_ea, 'name': ida_name.get_name(fn_ea) or '',
                            'pat': [{'vt': a, 'reg': b, 'off': c, 'store': d} for a, b, c, d in pat]})
    w('提取到布局的函数数 = %d' % len(layouts))
    w('')
    for L in layouts[:35]:
        w('##### %s @ 0x%X   写入 %d 处' % (L['name'] or '<noname>', L['fn'], len(L['pat'])))
        for p in L['pat']:
            w('   [%s+0x%X] <- %s' % (p['reg'], p['off'], p['vt']))
    json.dump(layouts, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False)

    # 3) 演示：解析出的构造函数里，主虚表写到偏移 0 的（真正的 ctor）
    w('')
    w('--- 主虚表写在偏移 0（典型构造函数）---')
    cnt = 0
    for L in layouts:
        zero = [p for p in L['pat'] if p['off'] == 0]
        if zero and len(L['pat']) > 1:
            cnt += 1
            if cnt <= 25:
                w('   %s: 多虚表类, 偏移=%s' % (L['name'] or hex(L['fn']),
                  ','.join('0x%X' % p['off'] for p in L['pat'])))
    w('   合计 %d 个多虚表构造点' % cnt)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)