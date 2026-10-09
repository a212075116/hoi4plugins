# -*- coding: utf-8 -*-
# ida_camera3.py -- 从 CCameraControlStrategy 的 TypeDescriptor 反查所有派生类
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment, ida_nalt
BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_camera3.txt'
lines = []
def w(s):
    lines.append(str(s)); print(s)
def d(ea):
    return ida_bytes.get_dword(ea)
def q(ea):
    return ida_bytes.get_qword(ea)
def rd(ea, n=300):
    b = ida_bytes.get_bytes(ea, n)
    if not b: return ''
    try: return b.split(b'\x00')[0].decode('ascii', 'replace')
    except Exception: return ''
def tdn(rva):
    td = BASE + rva
    if ida_segment.getseg(td) is None: return None
    s = rd(td + 0x10)
    return s if s.startswith('.?A') else None

TARGET = 'CCameraControlStrategy'
w('=' * 90)
w('一、找基类的 TypeDescriptor')
w('=' * 90)
n = ida_name.get_nlist_size()
td_of = {}
r3_of = {}
vt_of = {}
for i in range(n):
    s = ida_name.get_nlist_name(i)
    if not s: continue
    ea = ida_name.get_nlist_ea(i)
    if s.startswith('??_R0'):
        nm = s[5:].split('@@')[0]
        td_of[nm] = ea
    elif s.startswith('??_R3'):
        r3_of[s[5:].split('@@')[0]] = ea
    elif s.startswith('??_7'):
        vt_of.setdefault(s[4:].split('@@')[0], []).append((ea, s))
w('  TypeDescriptor 总数 %d, ClassHierarchyDescriptor 总数 %d, vftable 类总数 %d' % (len(td_of), len(r3_of), len(vt_of)))
td = None
for k, v in td_of.items():
    if TARGET in k:
        td = v; w('  匹配到的 TypeDescriptor key = %r' % k); break
w('  %s 的 TypeDescriptor = %s' % (TARGET, ('%#x' % td) if td else '未找到'))

if td:
    w('')
    w('=' * 90)
    w('二、谁引用这个 TypeDescriptor (这些就是 BaseClassDescriptor)')
    w('=' * 90)
    bcds = []
    for x in idautils.XrefsTo(td, 0):
        bcds.append(x.frm)
        w('  BaseClassDescriptor @ %#x' % x.frm)
    w('  共 %d 个' % len(bcds))
    w('')
    w('=' * 90)
    w('三、遍历所有 ClassHierarchyDescriptor, 找出基类链里含 %s 的类' % TARGET)
    w('=' * 90)
    derived = []
    for cls, ea in sorted(r3_of.items()):
        nb = d(ea + 0x08)
        if nb <= 0 or nb > 64: continue
        arr = BASE + d(ea + 0x0C)
        if ida_segment.getseg(arr) is None: continue
        hit = False
        chain = []
        for k in range(nb):
            dp = BASE + d(arr + k * 4)
            if ida_segment.getseg(dp) is None: break
            tn = tdn(dp)
            if tn: chain.append(tn)
            if tn and TARGET in tn: hit = True
        if hit:
            derived.append((cls, chain, ea))
    w('  派生类数量 = %d' % len(derived))
    for cls, chain, ea in derived:
        w('')
        w('  ### %s   (??_R3 @ %#x)' % (cls, ea))
        w('      基类链: %s' % ' <- '.join(chain))
        for vtea, sym in sorted(vt_of.get(cls, [])):
            w('      vftable %#x  %s' % (vtea, sym))
            k = 0
            while k < 40:
                p = q(vtea + k * 8)
                seg = ida_segment.getseg(p)
                if p == 0 or seg is None or not (seg.perm & 1): break
                k += 1
            w('        槽数=%d' % k)

    w('')
    w('=' * 90)
    w('四、派生类的虚函数反编译')
    w('=' * 90)
    for cls, chain, ea in derived:
        for vtea, sym in sorted(vt_of.get(cls, [])):
            k = 0
            while k < 12:
                p = q(vtea + k * 8)
                seg = ida_segment.getseg(p)
                if p == 0 or seg is None or not (seg.perm & 1): break
                nm = ida_name.get_name(p) or ''
                if nm == '_purecall':
                    k += 1; continue
                w('')
                w('--- %s [%#x] vfunc_%d @ %#x ---' % (cls, vtea, k, p))
                try:
                    cf = ida_hexrays.decompile(p)
                    if cf:
                        for ln in str(cf).split(chr(10))[:110]: w('    ' + ln)
                    else: w('    [无结果]')
                except Exception as e: w('    [失败] %s' % e)
                k += 1

with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(lines))
print('')
print('[写出] %s 行数=%d' % (OUT, len(lines)))
