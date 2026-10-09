# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CHI_师名字符串定位.txt'
TARGETS = ['37 Bubing Shi', '38 Bubing Shi', '132 Bubing Shi', '1 Lujun Shi', 'Shanghai Jingbei', 'Qingdao Jingbei']

pid, session, sc, fresh = connect(W + '/flirt/loader/_str_probe.js', tag='str')
wait_stable(sc, tag='str')
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 在堆里直接搜 CHI 的师名字符串, 定位师对象, 并读它周围的虚表与字段')
A('靶子       : history/units/CHI_1936.txt 的 division 名')
A('完整性     : 全量输出, 不抽样')
A('')
alls = {}
for t in TARGETS:
    r = sc.exports_sync.findStr(t)
    alls[t] = r
    A('=== %r  命中 %d 处  耗时 %d ms ===' % (t, len(r['hits']), r['ms']))
    for h in r['hits'][:8]:
        A('     %s' % h)
    A('')
detail = None
for t in TARGETS:
    hs = alls[t]['hits']
    if hs:
        detail = sc.exports_sync.probeAround(hs[0], 0x400, 0x400)
        A('=== 第一个命中的上下文: %r @ %s ===' % (t, hs[0]))
        A('  前后各 0x400 字节 (起始 %s):' % detail['start'])
        A('  该范围内命中的虚表地址 (off 是相对字符串地址的偏移):')
        for v in detail['vtHits']:
            A('     off=%+#x  %s  %s' % (v['off'], v['val'], v['vt']))
        A('  该范围内能读出的 CString:')
        for n in detail['names']:
            A('     off=%+#x  %r' % (n['off'], n['name']))
        A('  完整 0x800 字节:')
        h = detail['hex'] or ''
        for row in range(0, len(h), 32):
            A('     %+#06x  %s' % (row // 2 - 0x400, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
        A('')
        break
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for t in TARGETS:
    hs = alls[t]['hits']
    print('%-20r 命中 %-4d %s' % (t, len(hs), hs[:3]))
if detail:
    print('')
    print('上下文虚表命中:'); [print('   off=%+#x %s %s' % (v['off'], v['val'], v['vt'])) for v in detail['vtHits'][:10]]
    print('上下文 CString:'); [print('   off=%+#x %r' % (n['off'], n['name'])) for n in detail['names'][:10]]
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
