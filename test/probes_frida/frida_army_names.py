# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CHI_CArmy全量名字.txt'
pid, session, sc, fresh = connect(W + '/flirt/loader/_army_names.js', tag='armynames')
wait_stable(sc, tag='armynames')
d = sc.exports_sync.names()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('涉及类     : CGameState -> CCountry -> CArmy (继承 CUnit)')
A('涉及函数   : CArmy::ctor sub_140C6D470 / CShip 同族容器 sub_14011DF40')
A('测试目的   : 全量列出 CHI 的 85 个 CArmy 的名字与兵种, 与 OOB 对照')
A('靶子       : history/units/CHI_1936.txt 的 57 个 division')
A('完整性     : 全量输出, 不抽样')
A('')
A('CHI CArmy 数组 data = %s   count = %s' % (d.get('data'), d.get('count')))
A('')
A('%-4s %-20s %-10s %-8s %-8s %-22s %-22s %-14s %-24s' % ('#', 'CArmy*', 'vtable', '+0x18', '+0x1C', '自身名字', '模板名', '兵种', '单位名(+0x340->+0x60)'))
seen = []
for a in d.get('armies', []):
    A('%-4d %-20s %-10s %-8s %-8s %-22r %-22r %-14r %-24r' % (a['i'], a['ptr'], a['vt'], a['v18'], a['id1C'], a.get('name'), a.get('tmpl'), a.get('kind'), a.get('unitName')))
    if a.get('unitName'): seen.append(a['unitName'])
A('')
A('能读出名字的 CArmy 数 = %d' % len(seen))
A('名字去重后 %d 个:' % len(set(seen)))
for n in sorted(set(seen)): A('    %r' % n)
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('CArmy count = %s  有名字的 = %d' % (d.get('count'), len(seen)))
for a in d.get('armies', [])[:15]:
    print('  [%2d] %-20s tmpl=%-22r kind=%-12r unit=%r' % (a['i'], a['ptr'], a.get('tmpl'), a.get('kind'), a.get('unitName')))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
