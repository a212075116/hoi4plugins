# ida_fleet_owner2.py -- 读创建 CFleet 的几个小函数, 找容器
import idaapi, idautils, ida_funcs, ida_name, ida_bytes, idc, ida_hexrays

BASE = idaapi.get_imagebase()
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_fleet_owner2.txt'
lines = []
def w(s):
    lines.append(str(s))
    print(s)

def decomp(ea, n=120, label=''):
    w('')
    w('=' * 78)
    w('%s  %#x' % (label, ea))
    w('=' * 78)
    try:
        cf = ida_hexrays.decompile(ea)
        if cf:
            for ln in str(cf).split(chr(10))[:n]:
                w('    ' + ln)
    except Exception as e:
        w('    [失败] %s' % e)

SMALL = [
    (0x140D547F0, '创建CFleet的最小包装(66B)'),
    (0x140D55E40, '104B'),
    (0x1406D2EC0, '246B'),
    (0x140D54430, '195B 也用名字来源'),
    (0x140D5A430, '481B 也用名字来源'),
]
for ea, lbl in SMALL:
    decomp(ea, 130, lbl)

# 顺便把 sub_140D545A0 的完整反编译补上
decomp(0x140D545A0, 60, 'CFleet 创建函数 完整')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(lines))
print('')
print('[写出] %s' % OUT)