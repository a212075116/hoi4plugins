# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CArmy全量与词根搜索.txt'

pid, session, sc, fresh = connect(W + '/flirt/loader/_army2.js', tag='army2')
wait_stable(sc, tag='army2')
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : (a) 全量列出 CHI 的 CArmy (b) 用词根搜 OOB 师名是否真的在内存里')
A('完整性     : 全量输出, 不抽样')
A('')
d = sc.exports_sync.dumpAllArmies()
A('=== CHI 的 CArmy 数组 data=%s count=%s ===' % (d.get('data'), d.get('count')))
A('%-4s %-20s %-12s %-10s %-10s %-10s %-10s %s' % ('#', 'CArmy*', 'vtable', '+0x18', '+0x1C', '+0x28', '+0x2C', '+0x30'))
for a in d.get('armies', []):
    A('%-4d %-20s %-12s %-10s %-10s %-10s %-10s %s' % (a['i'], a['ptr'], a['vt'], a['v18'], a['v1C'], a['v28'], a['v2C'], a['v30']))
A('')
A('=== 词根搜索 ===')
for s in ('Bubing', 'Lujun', 'Jingbei', 'Sanjiao Jun', '37 '):
    r = sc.exports_sync.findStr(s, 200)
    A('  %-14r 命中 %-6d 耗时 %d ms' % (s, r['n'], r['ms']))
    for h in r['hits'][:12]:
        A('        %s' % h)
A('')
A('=== CArmy[0] 深度 dump (0x800 字节, 指针再下沉一层) ===')
if d.get('armies'):
    dp = sc.exports_sync.deepx(d['armies'][0]['ptr'], 0x800, 2)
    A('  CString 候选:')
    for n in dp['names']:
        A('     +0x%-4x %r' % (n['off'], n['name']))
    A('  指针字段:')
    for rf in dp['refs']:
        if rf['kind'] == 'vt': A('     +0x%-4x = %s  %s' % (rf['off'], rf['val'], rf['vt']))
        else:
            A('     +0x%-4x heap %s' % (rf['off'], rf['val']))
            for nn in (rf.get('names') or []): A('            +0x%-4x %r' % (nn['off'], nn['name']))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('CArmy count = %s' % d.get('count'))
for s in ('Bubing', 'Lujun', 'Jingbei', '37 '):
    r = sc.exports_sync.findStr(s, 20)
    print('%-12r 命中 %-5d %s' % (s, r['n'], r['hits'][:3]))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
