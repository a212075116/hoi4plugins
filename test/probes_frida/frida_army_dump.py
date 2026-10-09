# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
OUT = W + '/reports/20261009_015321_原版_CHI_CArmy_对象结构扫描.txt'

pid, session, sc, fresh = connect(W + '/flirt/loader/_army_dump.js', tag='armydump')
wait_stable(sc, tag='armydump')
d = sc.exports_sync.dumpArmies(N)
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 在 CArmy 对象里找出名字字段与 CUnit 容器的偏移')
A('靶子       : history/units/CHI_1936.txt 的 division, 例如 37 Bubing Shi')
A('完整性     : 全量输出, 不抽样' if d.get('armyCount') == len(d.get('armies', [])) else '完整性     : 只输出了前 %d 个, 共 %s 个' % (len(d.get('armies', [])), d.get('armyCount')))
A('')
A('CHI 的 CArmy 数组 data = %s   元素数 = %s' % (d.get('armyData'), d.get('armyCount')))
A('')
for a in d.get('armies', []):
    A('=' * 100)
    A('[CArmy %d] %s   虚表=%s' % (a['i'], a['ptr'], a['vt']))
    A('  名字类 CString 候选:')
    for n in a['names']:
        A('      +0x%-4x %r' % (n['off'], n['name']))
    A('  容器候选 (元素首 8 字节命中已知虚表):')
    for c in a['cand']:
        A('      off=+0x%-4x data=%s count=%s' % (c['off'], c['data'], c['count']))
        for h in c['hits']:
            A('           [%2d] %s  %s' % (h['i'], h['ptr'], h['vt']))
    A('  完整 0x400 字节:')
    h = a['hex'] or ''
    for row in range(0, len(h), 32):
        A('      +0x%03x  %s' % (row // 2, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
    A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('CArmy 数 = %s' % d.get('armyCount'))
for a in d.get('armies', []):
    print('[%d] %s 名字=%s' % (a['i'], a['ptr'], [n['name'] for n in a['names']][:4]))
    for c in a['cand']:
        print('     +0x%-4x count=%-6s %s' % (c['off'], c['count'], [(h['i'], h['vt']) for h in c['hits'][:5]]))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
