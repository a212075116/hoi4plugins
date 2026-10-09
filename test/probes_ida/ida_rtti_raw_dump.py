# -*- coding: utf-8 -*-
# 只读：直接 dump ??_R* 符号处的原始字节，反推真实 x64 布局
import os, json, traceback
import ida_pro, ida_auto, ida_name, ida_bytes, ida_segment
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
def hexdump(ea, n):
    b = ida_bytes.get_bytes(ea, n)
    if not b:
        return '  <no bytes>'
    out = []
    for off in range(0, len(b), 16):
        chunk = b[off:off+16]
        hx = ' '.join('%02X' % c for c in chunk)
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        out.append('  %08X  %-47s  %s' % (ea + off, hx, asc))
    return '\n'.join(out)
def rd_str(ea, n=180):
    b = ida_bytes.get_bytes(ea, n)
    if not b:
        return ''
    try:
        return b.split(b'\x00')[0].decode('ascii', 'replace')
    except Exception:
        return ''
try:
    ida_auto.auto_wait()
    tgt = {}
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if not s:
            continue
        for pre in ('??_R1A@', '??_R2', '??_R3', '??_R4'):
            if s.startswith(pre) and 'CPdxAllocator@@' in s and pre not in tgt:
                tgt[pre] = (s, ida_name.get_nlist_ea(i))
    for pre in ('??_R4', '??_R3', '??_R2', '??_R1A@'):
        if pre not in tgt:
            w('MISSING %s for CPdxAllocator' % pre)
            continue
        s, ea = tgt[pre]
        w('')
        w('===== %s @ 0x%X =====' % (s, ea))
        w(hexdump(ea, 0x40))
        w('  as qwords: ' + ' '.join('0x%X' % ida_bytes.get_qword(ea + k * 8) for k in range(8)))
        w('  as dwords: ' + ' '.join('0x%X' % ida_bytes.get_dword(ea + k * 4) for k in range(16)))
        # 若某个 qword 落在映射区且指向 TypeDescriptor 样式的字符串，打印之
        for k in range(8):
            p = ida_bytes.get_qword(ea + k * 8)
            if p and ida_segment.getseg(p):
                nm = rd_str(p + 0x10, 120)
                if nm.startswith('.'):
                    w('    [+0x%02X] 0x%X -> TypeDescriptor name=%s' % (k * 8, p, nm))
                nm2 = rd_str(p, 120)
                if nm2.startswith('.?A'):
                    w('    [+0x%02X] 0x%X -> direct name=%s' % (k * 8, p, nm2))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)