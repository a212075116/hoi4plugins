# ida_invalid2.py -- 查 Invalid_country_tag_0 到底是什么, 以及 CCharacter+8 的真实类型
#
# 上一轮动态预测失败(0/400), 读到 +0x08 = 0x49 即字符 'I'。
# 静态代码 *(_QWORD *)(a1 + 8) = Invalid_country_tag_0; 是写 8 字节,
# 所以 +0x08 很可能是"指针", 而不是 4 字节 CCountryTag 值。
#
# 本脚本查:
#   1. Invalid_country_tag_0 的符号类型与所在段(它是指针变量还是对象)
#   2. 谁引用它, 引用点附近在做什么
#   3. CCharacter 的 +8 在类型系统里是什么(若能拿到局部类型)
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_segment, ida_nalt

RVA = 0x333D528
ea = idaapi.get_imagebase() + RVA
print('=== Invalid_country_tag_0 @ %#x ===' % ea)
print('名称      : %s' % ida_name.get_name(ea))
seg = ida_segment.getseg(ea)
print('所在段    : %s' % (ida_segment.get_segm_name(seg) if seg else '?'))
print('段权限 flags: %#x' % (seg.perm if seg else 0))
print('8 字节内容: %#x' % ida_bytes.get_qword(ea))
print('4 字节内容: %#x' % ida_bytes.get_dword(ea))
print('')
print('=== 引用它的地方(前 25) ===')
n = 0
for x in idautils.XrefsTo(ea, 0):
    f = ida_funcs.get_func(x.frm)
    fn = ida_funcs.get_func_name(f.start_ea) if f else '?'
    print('  %#x  in %s' % (x.frm, fn))
    n += 1
    if n >= 25: break
print('总引用数(截断前统计): %d' % n)
print('')
print('=== 另一个符号 Invalid_country_tag (无 _0) ===')
for nm in ['Invalid_country_tag', 'Invalid_country_tag_0']:
    a = ida_name.get_name_ea(idaapi.BADADDR, nm)
    print('  %-28s -> %#x' % (nm, a))