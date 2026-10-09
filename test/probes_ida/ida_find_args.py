# -*- coding: utf-8 -*-
import os, json, traceback, re
import ida_pro, ida_auto, idaapi, ida_bytes, ida_strlist

cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()

try:
    ida_auto.auto_wait()
    qty = ida_strlist.get_strlist_qty()
    w('字符串总数 = %d' % qty)
    w('')
    w('=== 形如 -xxx 的命令行参数候选 ===')
    args = set()
    for i in range(qty):
        si = ida_strlist.string_info_t()
        if not ida_strlist.get_strlist_item(si, i):
            continue
        s = ida_bytes.get_strlit_contents(si.ea, si.length, si.type)
        if not s:
            continue
        try:
            t = s.decode('utf-8', 'replace')
        except Exception:
            continue
        if len(t) > 60 or len(t) < 2:
            continue
        # 形如 -abc 或 -abc= 的参数
        if re.fullmatch(r'-[a-zA-Z][a-zA-Z0-9_\-]{1,40}=?', t):
            args.add((t, si.ea))
    for t, ea in sorted(args):
        w('   0x%-10X %s' % (ea, t))
    w('   共 %d 个' % len(args))
    w('')
    w('=== 含 dll / plugin / load / inject / hook 的可疑字符串 ===')
    kws = ['plugin', '.dll', 'inject', 'loadlib', 'LoadLibrary', 'hook', 'mod_dll',
           'external', 'extension']
    cnt = 0
    for i in range(qty):
        si = ida_strlist.string_info_t()
        if not ida_strlist.get_strlist_item(si, i):
            continue
        s = ida_bytes.get_strlit_contents(si.ea, si.length, si.type)
        if not s: continue
        try:
            t = s.decode('utf-8', 'replace')
        except Exception:
            continue
        low = t.lower()
        if any(k.lower() in low for k in kws) and len(t) < 120:
            w('   0x%-10X %s' % (si.ea, t))
            cnt += 1
        if cnt > 60:
            w('   ... 截断'); break
    w('   命中 %d' % cnt)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)