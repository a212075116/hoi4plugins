# ida_find_managers.py -- 找 CCharacter/CFleet/CDecision/CEvent/CGameDate 的管理器
#
# 动态扫描已证明: 这 5 个类不在 CGameState 的 0..0x10000 顶层指针数组里,
# 也不在 CCountry 的 0..0x1710 里 => 应当由各自的管理器对象持有。
#
# 静态思路: 构造函数会写出自己的虚表指针。
#   lea rax, ??_7<Class>@@6B@ ; mov [rcx], rax
# 所以"引用该类虚表的函数"里就包含构造函数与其管理器。
# 用 xrefs 找引用虚表的函数, 再列出函数名/所在源文件线索。
import idaapi, idautils, idc, ida_funcs, ida_bytes, ida_name, ida_nalt
import json, os

TARGETS = {
    'CCharacter': 0x297EA60,
    'CFleet':     0x2962A18,
    'CDecision':  0x27EB3E8,
    'CEvent':     0x2999BE8,
    'CGameDate':  0x27183D8,
}
RESULT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/ida_managers.json'

out = {}
for cls, rva in TARGETS.items():
    ea = idaapi.get_imagebase() + rva
    name = ida_name.get_name(ea) or ''
    entry = {'rva': hex(rva), 'ea': hex(ea), 'vtname': name, 'refs': []}
    cnt = 0
    for xref in idautils.XrefsTo(ea, 0):
        f = ida_funcs.get_func(xref.frm)
        if f is None: continue
        fname = ida_funcs.get_func_name(f.start_ea) or ''
        entry['refs'].append({'from': hex(xref.frm), 'func': hex(f.start_ea), 'fname': fname})
        cnt += 1
        if cnt >= 40: break
    out[cls] = entry

with open(RESULT, 'w', encoding='utf-8') as fp:
    json.dump(out, fp, ensure_ascii=False, indent=1)

print('=== 引用各虚表的函数 ===')
for cls, e in out.items():
    print('')
    print('%s   虚表@%s  名称=%s   引用数=%d' % (cls, e['rva'], e['vtname'][:60], len(e['refs'])))
    seen = set()
    for r in e['refs']:
        if r['fname'] in seen: continue
        seen.add(r['fname'])
        print('    %-22s %s' % (r['func'], r['fname'][:70]))
        if len(seen) >= 14: break
print('')
print('[写出] %s' % RESULT)