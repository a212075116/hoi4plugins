# -*- coding: utf-8 -*-
"""虚表索引表的查询与分析工具。

用法:
  python vt_query.py <index.json> stats                 -- 总体统计
  python vt_query.py <index.json> find  <关键字>        -- 按类名/符号名查
  python vt_query.py <index.json> cls   <类名>          -- 精确查某个类
  python vt_query.py <index.json> slot  <槽RVA>         -- 哪些虚表用了这个槽
  python vt_query.py <index.json> shared <最少类数>      -- 被多个类共享的槽
"""
import sys, json, io
from collections import Counter, defaultdict


def load(p):
    return json.load(io.open(p, encoding='utf-8'))


def cmd_stats(d):
    vt = d['vt']
    print('虚表总数        : %d' % len(vt))
    print('RTTI 解析成功   : %d' % d['rtti_ok'])
    print('槽总数          : %d' % sum(v['n'] for v in vt))
    ns = [v['n'] for v in vt]
    print('槽数 最大/最小  : %d / %d' % (max(ns), min(ns)))
    print()
    print('槽数分布 (前 12):')
    for n, c in sorted(Counter(ns).items())[:12]:
        print('   %2d 槽 : %5d 个虚表' % (n, c))
    print()
    print('槽数最多的虚表 (前 10):')
    for v in sorted(vt, key=lambda x: -x['n'])[:10]:
        print('   n=%3d  %s' % (v['n'], v['cls'] or v['sym'][:60]))
    print()
    idx = defaultdict(int)
    for v in vt:
        for s in v['slots']:
            idx[s] += 1
    print('被引用最多的槽 (前 15):  槽RVA -> 被几个虚表使用')
    for s, c in sorted(idx.items(), key=lambda x: -x[1])[:15]:
        print('   %#010x : %d' % (s, c))


def cmd_find(d, kw):
    hits = [v for v in d['vt'] if kw.lower() in (v['cls'] or '').lower()
            or kw.lower() in v['sym'].lower()]
    print('匹配 %d 个:' % len(hits))
    for v in hits[:60]:
        print('   rva=%#010x n=%2d nbase=%s  %s' % (v['rva'], v['n'], v['nbase'], v['cls'] or v['sym']))


def cmd_cls(d, kw):
    hits = [v for v in d['vt'] if (v['cls'] or '') == kw]
    if not hits:
        print('未找到类 %s' % kw)
        return
    for v in hits:
        print('%s' % (v['cls'],))
        print('  rva    = %#010x' % v['rva'])
        print('  sym    = %s' % v['sym'])
        print('  nbase  = %s' % v['nbase'])
        print('  槽数    = %d' % v['n'])
        for i, s in enumerate(v['slots']):
            print('    [+0x%03X] slot[%2d] = %#010x' % (i * 8, i, s))


def cmd_slot(d, rva):
    rva = int(rva, 0)
    hits = [v for v in d['vt'] if rva in v['slots']]
    print('槽 %#x 被 %d 个虚表使用:' % (rva, len(hits)))
    for v in hits[:40]:
        idxs = [i for i, s in enumerate(v['slots']) if s == rva]
        print('   %-56s 槽位 %s' % (v['cls'] or v['sym'][:56],
                                    ['+0x%X' % (i * 8) for i in idxs]))


def cmd_shared(d, minc):
    minc = int(minc)
    m = defaultdict(list)
    for v in d['vt']:
        for i, s in enumerate(v['slots']):
            m[s].append((v['cls'] or v['sym'], i * 8))
    rows = [(s, l) for s, l in m.items() if len(l) >= minc]
    rows.sort(key=lambda x: -len(x[1]))
    print('被 >=%d 个类共享的槽: %d 个' % (minc, len(rows)))
    for s, l in rows[:30]:
        print('   %#010x : %d 个类   例: %s' % (s, len(l), l[0][0][:50]))


def main():
    p = sys.argv[1]
    d = load(p)
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'stats'
    a = sys.argv[3] if len(sys.argv) > 3 else None
    if cmd == 'stats':
        cmd_stats(d)
    elif cmd == 'find':
        cmd_find(d, a)
    elif cmd == 'cls':
        cmd_cls(d, a)
    elif cmd == 'slot':
        cmd_slot(d, a)
    elif cmd == 'shared':
        cmd_shared(d, a or 10)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
