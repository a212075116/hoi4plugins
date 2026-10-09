# ida_prov_state_layout.py -- 找 CProvince / CState 的构造函数与字段布局
#
# 依据: 用户指出 vtable 相等不足以证明对象是 Province/State, 需要拿出 id 和名字。
# 所以先静态确定这两个类的字段偏移。
#
# 做法: 构造函数里会写 vtable 并初始化各字段, 反编译即可看到偏移与初值。
# 另外把虚表每个槽列出(函数名/地址), 便于找 GetName/GetID 这类接口。
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
RESULT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_prov_state_layout.txt'

lines = []
def w(s):
    lines.append(str(s))
    print(s)

def vtable_slots(rva, name):
    ea = BASE + rva
    w('')
    w('=' * 78)
    w('虚表 %s @ RVA %#x' % (name, rva))
    w('=' * 78)
    cols = ida_bytes.get_qword(ea - 8)
    w('  COL 指针(虚表-8): %#x' % cols)
    for i in range(0, 80):
        p = ida_bytes.get_qword(ea + i * 8)
        if p == 0:
            w('  [%2d] (0) 结束' % i)
            break
        fmtd = ida_funcs.get_func(p)
        nm = ida_name.get_name(p) or ''
        fn = ida_funcs.get_func_name(p) if fmtd else ''
        sz = (fmtd.end_ea - fmtd.start_ea) if fmtd else 0
        w('  [%2d] %#x  %-34s %-22s size=%d' % (i, p, nm[:34], fn[:22], sz))

vtable_slots(0x2971B18, 'CProvince')
vtable_slots(0x2971B68, 'CProvince(2)')
vtable_slots(0x2936CC0, 'CState')
vtable_slots(0x2936D10, 'CState(2)')

for rva, name in ((0x2971B18, 'CProvince'), (0x2936CC0, 'CState')):
    ea = BASE + rva
    w('')
    w('=' * 78)
    w('引用 %s 虚表的函数' % name)
    w('=' * 78)
    seen = []
    for x in idautils.XrefsTo(ea, 0):
        f = ida_funcs.get_func(x.frm)
        if f is None: continue
        if f.start_ea in seen: continue
        seen.append(f.start_ea)
        fn = ida_funcs.get_func_name(f.start_ea) or ''
        w('  %#x  %-30s size=%d' % (f.start_ea, fn[:30], f.end_ea - f.start_ea))
    w('')
    cnt = 0
    for fstart in seen:
        w('')
        w('--- 反编译 %#x (%s) ---' % (fstart, ida_funcs.get_func_name(fstart)))
        try:
            cf = ida_hexrays.decompile(fstart)
            if cf:
                for ln in str(cf).split(chr(10))[:60]:
                    w('    ' + ln)
        except Exception as e:
            w('    [失败] %s' % e)
        cnt += 1
        if cnt >= 2: break

with open(RESULT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % RESULT)