# -*- coding: utf-8 -*-
# L2 演示：对一个类的全部虚函数反编译，从 this 的使用推断签名
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_funcs, ida_nalt, ida_typeinf, ida_hexrays, ida_lines, ida_bytes
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def infer_from_decomp(fea):
    """反编译并从 lvars 推断参数列表"""
    info = {'ok': False, 'defsig': None, 'args': [], 'ret': None, 'nlocals': 0, 'err': None}
    try:
        cf = ida_hexrays.decompile(fea)
        if not cf:
            info['err'] = 'decompile returned None'
            return info
        info['ok'] = True
        ti = ida_typeinf.tinfo_t()
        if ida_nalt.get_tinfo(ti, fea):
            info['defsig'] = ti.dstr()
        args = []
        for lv in cf.lvars:
            try:
                if lv.is_arg_var:
                    args.append((lv.name, lv.type().dstr()))
            except Exception:
                pass
        info['args'] = args
        info['nlocals'] = len(cf.lvars)
        # 返回类型
        try:
            t2 = cf.type
            if t2:
                info['ret'] = t2.dstr()
        except Exception:
            pass
        # 伪代码首行（含真实签名表述）
        sv = cf.get_pseudocode()
        if sv.size() > 0:
            info['header'] = ida_lines.tag_remove(sv[0].line)
    except Exception as e:
        info['err'] = str(e)
    return info
try:
    ida_auto.auto_wait()
    ok = ida_hexrays.init_hexrays_plugin()
    w('Hex-Rays = %s' % ok)
    w('')
    vt = json.load(open(cfg['vt_in'], encoding='utf-8'))['vt']
    base = ida_nalt.get_imagebase()
    target = cfg['cls']
    entries = [x for x in vt if x['cls'] == target]
    w('类 %s 有 %d 个虚表' % (target, len(entries)))
    w('')
    allres = []
    for e in entries:
        w('===== 虚表 0x%X  slots=%d =====' % (e['ea'], e['n']))
        ea = base + e['rva']
        rec = {'rva': e['rva'], 'n': e['n'], 'funcs': []}
        for k in range(e['n']):
            p = ida_bytes.get_qword(ea + k * 8)
            if not p:
                w('  [%2d] <null>' % k); continue
            nm = ida_name.get_name(p) or '<noname>'
            inf = infer_from_decomp(p)
            rec['funcs'].append({'slot': k, 'ea': p, 'name': nm, **inf})
            w('  [%2d] 0x%-12X %s' % (k, p, nm))
            if inf['ok']:
                w('        IDA签名: %s' % (inf['defsig'] or '<无>'))
                if 'header' in inf:
                    w('        伪代码首行: %s' % inf['header'])
                w('        参数(%d): %s' % (len(inf['args']),
                  ', '.join('%s %s' % (t, n) for n, t in inf['args']) or '<无>'))
                w('        局部变量数: %d' % inf['nlocals'])
            else:
                w('        反编译失败: %s' % inf['err'])
        allres.append(rec)
        w('')
    json.dump(allres, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False)
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)