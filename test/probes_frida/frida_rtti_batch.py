# -*- coding: utf-8 -*-
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
TS = '20261009_015321'
OUT = W + '/reports/%s_原版_IDA虚表命名_运行时RTTI全量核对.txt' % TS

vtlist = json.load(open(W + '/reports/vt_list.json', encoding='utf-8'))['vt']
print('虚表总数 %d' % len(vtlist), flush=True)

pid, session, sc, fresh = connect(W + '/flirt/loader/_rtti_batch.js', tag='rttibatch')
wait_stable(sc, tag='rttibatch')

def strip_rtti(nm):
    if not nm: return None
    # Frida readUtf8String(size) 读固定长度, 不按 NUL 截断 -> 这里手工截断
    s = nm.split('\x00')[0]
    for pre in ('.?AV', '.?AU', '.?AW4'):
        if s.startswith(pre): s = s[len(pre):]; break
    while s.endswith('@@'): s = s[:-2]
    return s

res = []
B = 400
for i in range(0, len(vtlist), B):
    chunk = vtlist[i:i+B]
    r = sc.exports_sync.batch([v['rva'] for v in chunk])
    res.extend(r)
    if (i // B) % 8 == 0: print('  进度 %d/%d' % (min(i+B, len(vtlist)), len(vtlist)), flush=True)
print('采集完成 %d 条' % len(res), flush=True)

same = []; diff = []; nocol = []; notd = []; trunc = []
for v, r in zip(vtlist, res):
    cls = v.get('cls')
    if r.get('err'):
        (nocol if r['err'] == 'noCOL' else notd).append((v, r, cls))
        continue
    rt = strip_rtti(r.get('name'))
    if rt == cls: same.append((v, r, cls, rt))
    elif rt and cls and rt.startswith(cls): trunc.append((v, r, cls, rt))
    else: diff.append((v, r, cls, rt))

L = []
def A(s): L.append(str(s))
A('时间戳     : %s' % TS)
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('静态来源   : reports/vt_list.json  (IDA 通过 RTTI 自动命名, 共 %d 张虚表)' % len(vtlist))
A('动态来源   : 运行时直接读 vftable-0x8 的 RTTICompleteObjectLocator -> TypeDescriptor -> 类名')
A('测试目的   : 核对 IDA 静态分析给出的虚表类名与运行时 RTTI 真名是否一致, 统计正确数量')
A('完整性     : 全量输出, 不抽样')
A('')
A('=== 汇总 ===')
A('  虚表总数          : %d' % len(vtlist))
A('  读到 RTTI 且完全一致 : %d' % len(same))
A('  运行时的名字以 IDA 名字为前缀(IDA 名被截断) : %d' % len(trunc))
A('  读到 RTTI 但真不一致 : %d' % len(diff))
A('  COL 为空(无 RTTI) : %d' % len(nocol))
A('  有 COL 但无 TD     : %d' % len(notd))
A('  可判定的一致率    : %d / %d  (完全一致 / (完全一致+截断+真不一致))' % (len(same), len(same) + len(trunc) + len(diff)))
A('  含截断的一致率    : %d / %d' % (len(same) + len(trunc), len(same) + len(trunc) + len(diff)))
A('')
A('=== IDA 名被截断清单(全量) ===')
if not trunc: A('  (无)')
for v, r, cls, rt in trunc:
    A('  rva=%#010x n=%-4d IDA=%r' % (v['rva'], v['n'], cls))
    A('        运行时完整名=%r' % rt)
A('')
A('=== 不一致清单(全量) ===')
if not diff: A('  (无)')
for v, r, cls, rt in diff:
    A('  rva=%#010x n=%-4d IDA=%r  运行时=%r  col=%s' % (v['rva'], v['n'], cls, rt, r.get('col')))
A('')
A('=== 无 RTTI 的虚表(COL 指针为空, 全量) ===')
if not nocol: A('  (无)')
for v, r, cls in nocol:
    A('  rva=%#010x n=%-4d IDA=%r' % (v['rva'], v['n'], cls))
A('')
A('=== 有 COL 但 TypeDescriptor RVA 为 0(全量) ===')
if not notd: A('  (无)')
for v, r, cls in notd:
    A('  rva=%#010x n=%-4d IDA=%r  err=%s' % (v['rva'], v['n'], cls, r.get('err')))
A('')
A('=== 一致清单(全量, rva / 槽数 / 类名) ===')
for v, r, cls, rt in same:
    A('  rva=%#010x n=%-5d %s' % (v['rva'], v['n'], cls))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('总数 %d  完全一致 %d  截断 %d  真不一致 %d  COL空 %d  TD空 %d' % (len(vtlist), len(same), len(trunc), len(diff), len(nocol), len(notd)))
print('可判定一致率: %d/%d' % (len(same), len(same)+len(trunc)+len(diff)))
for v, r, cls, rt in diff[:15]:
    print('  不一致 rva=%#x IDA=%r 运行时=%r' % (v['rva'], cls, rt))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
