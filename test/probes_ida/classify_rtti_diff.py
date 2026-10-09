# -*- coding: utf-8 -*-
import re, ast, json, collections

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
TS = '20261009_015321'
SRC = W + '/reports/%s_原版_IDA虚表命名_运行时RTTI全量核对.txt' % TS
OUT = W + '/reports/%s_原版_IDA虚表命名_1358条不一致分类.txt' % TS

txt = open(SRC, encoding='utf-8').read()
lines = txt.split(chr(10))

# 定位三个清单小节
def sect(name):
    for i, l in enumerate(lines):
        if l.startswith('=== ') and name in l: return i
    return -1
i_diff = sect('不一致清单')
i_nocol = sect('无 RTTI 的虚表')
i_notd = sect('TypeDescriptor RVA 为 0')
i_same = sect('一致清单')
diff_block = lines[i_diff:i_nocol]

RX = re.compile(r"^\s+rva=(0x[0-9a-fA-F]+)\s+n=(\d+)\s+IDA=(.*?)\s+运行时=(.*?)\s+col=(.*)$")
rows = []
for l in diff_block:
    m = RX.match(l)
    if not m: continue
    rva, n, ida, rt, col = m.groups()
    try: ida = ast.literal_eval(ida)
    except Exception: pass
    try: rt = ast.literal_eval(rt)
    except Exception: pass
    rows.append({'rva': int(rva, 16), 'n': int(n), 'ida': ida, 'rt': rt, 'col': col})

def norm(s):
    if s is None: return ''
    # IDA 把 C++ 修饰名里的 < > 换成 _, 这里统一这些非标识符字符
    for ch in '<>_,-`:':
        s = s.replace(ch, '_')
    return s

cats = collections.Counter()
buckets = collections.defaultdict(list)
for r in rows:
    a, b = r['ida'] or '', r['rt'] or ''
    if norm(a) == norm(b):
        k = 'A. 仅符号字符规范化差异(IDA 把 < > 写成 _)'
    elif norm(b).startswith(norm(a)):
        k = 'B. IDA 名是运行时名的前缀(被截断)'
    elif norm(a).startswith(norm(b)):
        k = 'C. 运行时名是 IDA 名的前缀'
    else:
        k = 'D. 其它(需人工看)'
    cats[k] += 1
    buckets[k].append(r)

L = []
def A(s): L.append(str(s))
A('时间戳     : %s' % TS)
A('来源       : %s' % SRC)
A('测试目的   : 把 %d 条「IDA 名字与运行时 RTTI 名字不一致」逐条分类, 看其中多少只是命名规范化差异' % len(rows))
A('完整性     : 全量输出, 不抽样')
A('')
A('=== 分类汇总 ===')
for k in sorted(cats): A('  %-46s %d' % (k, cats[k]))
A('  合计                                       %d' % len(rows))
A('')
for k in sorted(buckets):
    A('=== %s  (共 %d 条, 全量) ===' % (k, len(buckets[k])))
    for r in buckets[k]:
        A('  rva=%#010x n=%-4d IDA=%r' % (r['rva'], r['n'], r['ida']))
        A('       运行时=%r' % r['rt'])
    A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)))
print('')
for k in sorted(cats): print('  %-46s %d' % (k, cats[k]))
print('  合计 %d' % len(rows))
print('')
for k in sorted(buckets):
    if k.startswith('D.'):
        print('--- D 类前 15 条 ---')
        for r in buckets[k][:15]:
            print('  rva=%#x IDA=%r' % (r['rva'], r['ida']))
            print('        运行时=%r' % r['rt'])
