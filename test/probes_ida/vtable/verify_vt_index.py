# -*- coding: utf-8 -*-
"""校验虚表索引表 (复现自检工具)。

用法:
    python verify_vt_index.py <你的索引.json> [参考索引.json]

不带参考文件时, 只做"游戏决定的硬指标"校验 (数量 / 关键类 / 端到端槽位)。
带参考文件时, 额外逐条比对 rva / slots / cls。
"""
import sys, io, json

# 这些值由 hoi4.exe 1.19.3 本身决定, 与工具无关, 必须一致
EXPECT_COUNT = 12333
EXPECT_RTTI_OK = 12333
EXPECT_SLOT_TOTAL = 496650

# 关键类: 类名 -> (虚表RVA, 槽数)
KEY_CLASSES = {
    'CInGameIdler':     (0x02968FF0, 64),
    'CFrontEndIdler':   (0x02949D50, 64),
    'CCurrentGameState': (0x02721158, 45),
    'CCountry':         (0x027E7360, 64),
    'CArmy':            (0x0295A2B0, 64),
}

# 端到端校验: CInGameIdler 的 +0x130 槽必须是 cam getter
E2E_CLASS = 'CInGameIdler'
E2E_SLOT_IDX = 38          # +0x130 / 8
E2E_SLOT_RVA = 0x00DC53B0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    mine = json.load(io.open(sys.argv[1], encoding='utf-8'))
    ref_path = sys.argv[2] if len(sys.argv) > 2 else None

    fails = []

    print('=== 硬指标校验 (与工具无关, 由游戏本身决定) ===')
    cnt = mine['count']
    ok = mine['rtti_ok']
    total = sum(len(v['slots']) for v in mine['vt'])
    for label, got, want in [('虚表总数', cnt, EXPECT_COUNT),
                             ('RTTI 成功', ok, EXPECT_RTTI_OK),
                             ('槽总数', total, EXPECT_SLOT_TOTAL)]:
        flag = 'OK ' if got == want else '** 不一致 **'
        print('  %-12s %8d   期望 %8d   %s' % (label, got, want, flag))
        if got != want:
            fails.append(label)

    print()
    print('=== 关键类校验 ===')
    byname = {}
    for v in mine['vt']:
        if v['cls']:
            byname.setdefault(v['cls'], []).append(v)
    for name, (rva, n) in KEY_CLASSES.items():
        lst = byname.get(name) or []
        hit = [v for v in lst if v['rva'] == rva]
        if not hit:
            print('  %-20s 未找到 rva=%#010x 的虚表  ** 失败 **' % (name, rva))
            fails.append(name)
            continue
        v = hit[0]
        flag = 'OK ' if v['n'] == n else '** 槽数 %d 期望 %d **' % (v['n'], n)
        print('  %-20s rva=%#010x  n=%2d  %s' % (name, rva, v['n'], flag))
        if v['n'] != n:
            fails.append(name + '(槽数)')

    print()
    print('=== 端到端校验 ===')
    v = (byname.get(E2E_CLASS) or [None])[0]
    if v is None:
        print('  找不到 %s  ** 失败 **' % E2E_CLASS)
        fails.append(E2E_CLASS)
    elif E2E_SLOT_IDX >= v['n']:
        print('  %s 只有 %d 个槽, 取不到槽[%d]  ** 失败 **' % (E2E_CLASS, v['n'], E2E_SLOT_IDX))
        fails.append('E2E')
    else:
        got = v['slots'][E2E_SLOT_IDX]
        flag = 'OK ' if got == E2E_SLOT_RVA else '** 得到 %#x, 期望 %#x **' % (got, E2E_SLOT_RVA)
        print('  %s 槽[%d] (+0x%X) = %#010x   %s'
              % (E2E_CLASS, E2E_SLOT_IDX, E2E_SLOT_IDX * 8, got, flag))
        if got != E2E_SLOT_RVA:
            fails.append('E2E 槽位')

    if ref_path:
        print()
        print('=== 与参考索引表逐条比对 ===')
        ref = json.load(io.open(ref_path, encoding='utf-8'))
        da = {v['rva']: v for v in mine['vt']}
        db = {v['rva']: v for v in ref['vt']}
        same_set = set(da) == set(db)
        print('  rva 集合相同        : %s' % same_set)
        if not same_set:
            fails.append('rva 集合')
        diff_slots = [r for r in da if r in db and da[r]['slots'] != db[r]['slots']]
        diff_cls = [r for r in da if r in db and da[r].get('cls') != db[r].get('cls')]
        print('  slots 不同的条数    : %d' % len(diff_slots))
        print('  cls   不同的条数    : %d' % len(diff_cls))
        if diff_slots:
            fails.append('slots 差异')
            for r in diff_slots[:5]:
                print('    rva=%#x  我 %d 槽 / 参考 %d 槽'
                      % (r, len(da[r]['slots']), len(db[r]['slots'])))
        if diff_cls:
            fails.append('cls 差异')
            for r in diff_cls[:5]:
                print('    rva=%#x  我 %r / 参考 %r' % (r, da[r].get('cls'), db[r].get('cls')))
        # sym 刻意不比: 它来自 IDA 符号表, 会因 demangler / FLIRT 差异而变
        print('  (sym 不比对: 它由 IDA 符号表决定, 可能因人而异)')

    print()
    if fails:
        print('结论: ** 校验未通过 **, 不一致项: %s' % ', '.join(fails))
        return 1
    print('结论: 校验通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
