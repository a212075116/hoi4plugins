# ida_ctor_analysis.py -- 反编译剩余 5 个类的构造函数, 并找出谁调用它们
#
# 依据: 虚表引用数极少(CCharacter=3, CFleet=2, CEvent=2) => 这些引用点就是构造函数。
# 构造函数能给出两件关键信息:
#   1. operator new 的参数 => 对象大小
#   2. 调用它的函数   => 哪一层容器持有这些对象(顺藤摸瓜找到管理器)
import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, idc

BASE = idaapi.get_imagebase()
TARGETS = {
    'CCharacter': [0x140F9EC50, 0x140F9EEA0, 0x140F9F180],
    'CFleet':     [0x140D503D0, 0x140D50840],
    'CDecision':  [0x140722F50, 0x140723280, 0x140724250],
    'CEvent':     [0x14117F1A0, 0x14117F400],
}
RESULT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_ctors.txt'

lines = []
def w(s):
    lines.append(s)
    print(s)

for cls, addrs in TARGETS.items():
    w('')
    w('=' * 78)
    w('## %s' % cls)
    w('=' * 78)
    for a in addrs:
        f = ida_funcs.get_func(a)
        if f is None:
            w('  %#x  (不是函数)' % a)
            continue
        size = f.end_ea - f.start_ea
        w('')
        w('--- %#x  大小=%d 字节 ---' % (a, size))
        # 调用者
        callers = []
        for x in idautils.XrefsTo(f.start_ea, 0):
            cf = ida_funcs.get_func(x.frm)
            if cf is None: continue
            cn = ida_funcs.get_func_name(cf.start_ea) or ''
            callers.append('%#x %s' % (cf.start_ea, cn))
        w('  调用者(%d): %s' % (len(callers), ' | '.join(callers[:8])))
        # 反编译
        try:
            cf = ida_hexrays.decompile(a)
            if cf:
                txt = str(cf)
                for ln in txt.split(chr(10))[:70]:
                    w('    ' + ln)
        except Exception as e:
            w('    [反编译失败] %s' % e)

with open(RESULT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % RESULT)