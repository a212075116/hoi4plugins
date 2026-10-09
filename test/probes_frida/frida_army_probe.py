# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable, find_pid

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CHI_CCountry_CArmy容器扫描.txt'

pid, session, sc, fresh = connect(W + '/flirt/loader/_army_probe.js', tag='army')
wait_stable(sc, tag='army')
d = sc.exports_sync.scanCountry()
dc = sc.exports_sync.dumpCountry()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 在 CHI 的 CCountry 对象里找出 CArmy / CUnit 的容器偏移')
A('完整性     : 全量输出, 不抽样')
A('')
A('CHI CCountry* = %s' % d.get('chiPtr'))
A('')
A('--- CCountry 的全部 0x600 字节 ---')
h = dc.get('hex') or ''
for row in range(0, len(h), 32):
    A('  +0x%03x  %s' % (row // 2, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
A('')
A('--- 看起来像 (指针数组, 数量) 的偏移, 且前几个元素的首 8 字节命中已知虚表 ---')
for o in d.get('offsets', []):
    A('  off=+0x%-4x data=%s count=%s' % (o['off'], o['data'], o['count']))
    for hh in o['hits']:
        A('       [%2d] %s  %s' % (hh['i'], hh['ptr'], hh['vt']))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for o in d.get('offsets', []):
    print('off=+0x%-4x count=%-6s %s' % (o['off'], o['count'], [(h['i'], h['vt']) for h in o['hits'][:6]]))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
