# -*- coding: utf-8 -*-
import json, io, collections, os
W = r'D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV'
src = os.path.join(W, 'reports', 'rtti_hierarchy.json')
d = json.load(open(src, 'r', encoding='utf-8'))
per = d['per_class']
edges = d['edges']
kids = collections.defaultdict(list)
for c, b in edges:
    kids[b].append(c)
withbases = {c: b for c, b in per.items() if b}
roots = [c for c in per if not per[c]]
basecnt = collections.Counter(b for _, b in edges)
depth = {}
def dep_of(c, seen=None):
    if c in depth:
        return depth[c]
    if seen is None:
        seen = set()
    if c in seen:
        return 0
    seen.add(c)
    bs = per.get(c) or []
    v = 0 if not bs else 1 + max((dep_of(b, seen) for b in bs), default=0)
    seen.discard(c)
    depth[c] = v
    return v
for c in list(per)[:20000]:
    dep_of(c)
dd = collections.Counter(depth.values())
L = []
A = L.append
A('# hoi4.exe 类继承层次（从 MSVC RTTI 恢复）')
A('')
A('> 数据源：数据库内 IDA 已解析的 `??_R2` / `??_R3` 结构（17621 组）')
A('> 恢复方式：按实测的 x64 RTTI 布局直接读结构（结构内指针为 4 字节 RVA）')
A('')
A('## 一、总览')
A('')
A('| 指标 | 数值 |')
A('| --- | --- |')
A('| 解析成功 | **%d / %d**（跳过 0） |' % (len(per), len(per)))
A('| 有基类的类 | **%d** |' % len(withbases))
A('| 无基类（根类） | %d |' % len(roots))
A('| 继承边总数 | **%d** |' % len(edges))
A('| 基类数 >= 4 的类 | %d |' % sum(1 for b in per.values() if len(b) >= 4))
A('| 最大基类数 | %d |' % max((len(b) for b in per.values()), default=0))
A('| 最深继承层数 | %d |' % max(depth.values(), default=0))
A('')
A('继承深度分布：' + ', '.join('%d 层=%d' % (k, v) for k, v in sorted(dd.items())))
A('')
A('## 二、被继承最多的基类（引擎骨架）')
A('')
A('| 基类 | 直接子类数 |')
A('| --- | --- |')
for b, c in basecnt.most_common(40):
    A('| `%s` | %d |' % (b, c))
A('')
A('## 三、继承最深的类')
A('')
deep = sorted(((c, b) for c, b in per.items() if b), key=lambda x: (-len(x[1]), x[0]))
A('| 类 | 基类数 | 继承链（派生 -> 基） |')
A('| --- | --- | --- |')
for c, b in deep[:30]:
    A('| `%s` | %d | %s |' % (c, len(b), ' < '.join('`%s`' % x for x in ([c] + b))))
A('')
A('## 四、完整继承链（按字母序，%d 个类）' % len(withbases))
A('')
A('```')
for c in sorted(withbases):
    A('%s : %s' % (c, ', '.join(withbases[c])))
A('```')
out = os.path.join(W, 'reports', '类继承层次.md')
open(out, 'w', encoding='utf-8').write('\n'.join(L))
print('written: ' + out)
print('size: %.1f KB' % (os.path.getsize(out) / 1024))
print('classes=%d withbases=%d edges=%d maxbases=%d maxdepth=%d'
      % (len(per), len(withbases), len(edges), max((len(b) for b in per.values()), default=0), max(depth.values(), default=0)))