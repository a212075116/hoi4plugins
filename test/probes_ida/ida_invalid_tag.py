# ida_invalid_tag.py -- 定位全局对象 Invalid_country_tag, 它是国家数组的持有者
#
# 线索(来自 CChangeTagEffect 反编译):
#   *((_DWORD *)Invalid_country_tag + 181) = 数组大小      => 对象 +724
#   *((_QWORD *)Invalid_country_tag + 89)  = 数组基址      => 对象 +712
#   Invalid_country_tag[98]                 = 另一个数组  => 对象 +784
# 且元素是指针, 元素 +8 是 4 字节(与 CCountry+0x08 索引吻合)。
#
# 目标: 找到该对象的静态地址, 并找出它的类型/构造位置, 便于动态读取。
import idaapi, idautils, ida_funcs, ida_hexrays, ida_name, ida_bytes, ida_segment

OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_invalid_tag.txt'
base = idaapi.get_imagebase()
lines = []
def w(s):
    lines.append(s)
    print(s, flush=True)

w('# 查找 Invalid_country_tag')
hits = []
for ea, nm in idautils.Names():
    if 'Invalid_country_tag' in nm:
        hits.append((ea, nm))
w('符号数: %d' % len(hits))
for ea, nm in hits[:10]:
    w('  %#x  %s   (RVA %#x)' % (ea, nm, ea - base))
    seg = ida_segment.getseg(ea)
    if seg: w('        段=%s' % ida_segment.get_segm_name(seg))

# 该名字附近的字符串(确认语义)
w('')
w('# 名字里含 invalid 的字符串常量')
cnt = 0
for ea, nm in idautils.Names():
    low = nm.lower()
    if 'invalid' in low and ('tag' in low or 'country' in low):
        cnt += 1
        if cnt <= 20:
            s = ida_bytes.get_strlit_contents(ea, -1, 0)
            w('  %#x  %s  = %s' % (ea, nm, (s or b'').decode('utf-8', 'replace')[:90]))
w('共 %d' % cnt)

# 若有命中, 反编译引用它的函数
if hits:
    tgt = hits[0][0]
    w('')
    w('# 引用 %#x 的函数(最多 6 个)' % tgt)
    n = 0
    for xr in idautils.XrefsTo(tgt, 0):
        f = ida_funcs.get_func(xr.frm)
        if f is None: continue
        w('  --- %#x %s' % (f.start_ea, ida_name.get_name(f.start_ea) or '?'))
        n += 1
        if n >= 6: break

# 顺便: 查找含 countrytagalias.cpp 的字符串, 那是 tag 别名实现
w('')
w('# countrytagalias / countrytag 相关源文件字符串')
for ea, nm in idautils.Names():
    try:
        s = ida_bytes.get_strlit_contents(ea, -1, 0)
    except Exception:
        continue
    if s and b'countrytag' in s.lower():
        w('  %#x  %s' % (ea, s.decode('utf-8', 'replace')[:110]))

open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines))
print('written: ' + OUT, flush=True)
idaapi.qexit(0)