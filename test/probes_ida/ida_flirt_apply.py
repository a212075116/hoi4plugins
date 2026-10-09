# -*- coding: utf-8 -*-
# 通用 FLIRT 批量应用器：配置经环境变量 FLIRT_JOB 指向的 JSON 传入
import os, json, time, traceback
import ida_funcs, ida_auto, ida_pro, ida_nalt, ida_kernwin

UNNAMED = ('sub_', 'unknown_', 'nullsub_', 'j_sub_', 'locret_', 'def_')

def snapshot():
    qty = ida_funcs.get_func_qty()
    unnamed = 0
    for i in range(qty):
        f = ida_funcs.getn_func(i)
        if f is None:
            continue
        nm = ida_funcs.get_func_name(f.start_ea)
        if not nm or nm.startswith(UNNAMED):
            unnamed += 1
    return {'func_qty': qty, 'unnamed': unnamed, 'named': qty - unnamed}

def main():
    cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
    out = cfg['output']
    f = open(out, 'w', encoding='utf-8')
    def log(s):
        f.write(str(s) + '\n'); f.flush()
    result = {'kernel': None, 'input': None, 'before': None, 'after': None, 'items': [], 'planned': len(cfg['signatures'])}
    try:
        result['kernel'] = ida_kernwin.get_kernel_version()
        result['input'] = ida_nalt.get_input_file_path()
        log('kernel=%s input=%s' % (result['kernel'], result['input']))
        ida_auto.auto_wait()
        t0 = time.time()
        result['before'] = snapshot()
        log('BEFORE %s  (%.1fs)' % (json.dumps(result['before']), time.time() - t0))
        sigs = cfg['signatures']
        t1 = time.time()
        plan = []
        for i, p in enumerate(sigs):
            r = ida_funcs.plan_to_apply_idasgn(p)
            plan.append({'idx': i, 'ret': int(r), 'exists': os.path.exists(p), 'sig': os.path.basename(p), 'path': p})
        result['plan'] = plan
        log('planned %d sigs in %.1fs' % (len(sigs), time.time() - t1))
        t2 = time.time()
        ida_auto.auto_wait()
        log('auto_wait finished in %.1fs' % (time.time() - t2))
        t3 = time.time()
        result['after'] = snapshot()
        log('AFTER  %s  (%.1fs)' % (json.dumps(result['after']), time.time() - t3))
        n = ida_funcs.get_idasgn_qty()
        log('idasgn_qty=%d' % n)
        for i in range(n):
            try:
                d = ida_funcs.get_idasgn_desc_with_matches(i)
            except Exception:
                d = ida_funcs.get_idasgn_desc(i)
            st = ida_funcs.calc_idasgn_state(i)
            log('  [%d] state=%d desc=%s' % (i, st, d))
            result['items'].append({'index': i, 'state': int(st), 'desc': [str(x) for x in d] if isinstance(d, (tuple, list)) else str(d)})
        json.dump(result, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        log('DONE')
    except Exception:
        log('EXC ' + traceback.format_exc())
        try:
            json.dump(result, open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        except Exception:
            pass
    finally:
        f.close()
        ida_pro.qexit(0)

main()