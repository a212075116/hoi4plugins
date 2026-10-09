# -*- coding: utf-8 -*-
import os, json, traceback
import ida_pro, ida_auto, idaapi, idautils, ida_funcs, ida_name, ida_bytes
import ida_lines, ida_strlist, idc

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()

def ov(ea, n):
    try:
        return idc.get_operand_value(ea, n)
    except Exception:
        return None

def str_at(ea):
    if not ea:
        return None
    s = ida_bytes.get_strlit_contents(ea, -1, 0)
    if not s:
        return None
    try:
        return s.decode('utf-8', 'replace')
    except Exception:
        return repr(s)

TARGETS = ['LoadLibraryA', 'LoadLibraryW', 'LoadLibraryExW']

try:
    ida_auto.auto_wait()
    addrs = {}
    for t in TARGETS:
        ea = ida_name.get_name_ea(idaapi.BADADDR, t)
        if ea != idaapi.BADADDR:
            addrs[t] = ea
    w('=== LoadLibrary* 调用点与传入路径 ===')
    for t, ea in addrs.items():
        callers = list(idautils.CodeRefsTo(ea, 0))
        w('')
        w('===== %s : %d 个调用点 =====' % (t, len(callers)))
        for c in callers:
            fn = ida_funcs.get_func(c)
            fname = ida_name.get_name(fn.start_ea) if fn else '?'
            hit = None
            cur = c
            for back in range(1, 25):
                cur = ida_bytes.prev_head(cur, 0)
                if cur == idaapi.BADADDR:
                    break
                txt = ida_lines.tag_remove(ida_lines.generate_disasm_line(cur, 0))
                ts = txt.strip()
                if not (ts.startswith('lea') or ts.startswith('mov')):
                    continue
                if not ('rcx' in ts or 'rdx' in ts):
                    continue
                op = ov(cur, 1)
                if op and op > 0x10000:
                    s = str_at(op)
                    if s and len(s) > 2:
                        hit = s
                        break
            w('  0x%-10X %-36s -> %s' % (c, fname[:36], ('"' + hit[:110] + '"') if hit else '(动态/未解析)'))
    w('')

    w('=== 含 mod/dll/workshop 关键字的字符串 ===')
    kws = ['mod/', 'workshop', 'paradox interactive', '.dll', 'content/', 'userdir', 'modlist', 'dlc']
    cnt = 0
    qty = ida_strlist.get_strlist_qty()
    w('  字符串总数 = %d' % qty)
    for i in range(qty):
        si = ida_strlist.string_info_t()
        if not ida_strlist.get_strlist_item(si, i):
            continue
        s = ida_bytes.get_strlit_contents(si.ea, si.length, si.type)
        if not s:
            continue
        try:
            txt = s.decode('utf-8', 'replace')
        except Exception:
            continue
        low = txt.lower()
        if any(k in low for k in kws) and len(txt) < 150:
            w('   0x%-10X %s' % (si.ea, txt))
            cnt += 1
        if cnt > 100:
            w('   ... 截断')
            break
    w('  命中数 = %d' % cnt)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)