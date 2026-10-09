# -*- coding: utf-8 -*-
# 导出全部 vftable 的 RVA 与类名，供 frida 内存扫描使用
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_nalt, ida_segment, ida_bytes
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
try:
    ida_auto.auto_wait()
    base = ida_nalt.get_imagebase()
    out = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s or not s.startswith('??_7'):
            continue
        ea = ida_name.get_nlist_ea(i)
        cls = s[4:].split('@@')[0]
        # 槽位数：读到第一个非代码指针
        k = 0
        while k < 1024:
            p = ida_bytes.get_qword(ea + k * 8)
            seg = ida_segment.getseg(p)
            if p == 0 or seg is None or not (seg.perm & 1):
                break
            k += 1
        out.append({'sym': s, 'cls': cls, 'ea': ea, 'rva': ea - base, 'n': k})
    json.dump({'imagebase': base, 'count': len(out), 'vt': out},
              open(cfg['json'], 'w', encoding='utf-8'), ensure_ascii=False)
except Exception:
    open(cfg['output'], 'w', encoding='utf-8').write(traceback.format_exc())
ida_pro.qexit(0)