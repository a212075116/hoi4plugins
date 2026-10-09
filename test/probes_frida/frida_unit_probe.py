# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CUnit_实例与名字字段探测.txt'

pid, session, sc, fresh = connect(W + '/flirt/loader/_unit_probe.js', tag='unit')
wait_stable(sc, tag='unit')
print('[扫描 CUnit 虚表 0x29530D8 + 探测前 25 个的名字字段]', flush=True)
d = sc.exports_sync.scanUnits(25, 0x600)
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 统计 CUnit 实例数, 并在前若干实例上定位名字字段偏移')
A('靶子       : history/units/CHI_1936.txt 的 division 名, 例如 37 Bubing Shi')
A('完整性     : 全量统计; 字段探测只取前 %d 个实例(探测性质, 非结论)' % 25)
A('')
A('CUnit 实例总数 = %s   扫描耗时 = %s ms   探测耗时 = %s ms' % (d.get('total'), d.get('scanMs'), d.get('probeMs')))
A('')
for p in d.get('probes', []):
    A('[CUnit %d] %s' % (p['i'], p['ptr']))
    A('   名字类 CString 候选:')
    for n in p['names']:
        A('      +0x%-4x %r' % (n['off'], n['name']))
    A('   前 0x200 字节:')
    h = p['hex'] or ''
    for row in range(0, len(h), 32):
        A('      +0x%03x  %s' % (row // 2, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
    A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('CUnit 实例总数 = %s' % d.get('total'))
for p in d.get('probes', [])[:8]:
    print('[%2d] %s  名字=%s' % (p['i'], p['ptr'], [n['name'] for n in p['names']][:4]))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
