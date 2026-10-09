# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_摄像机相关实例扫描.txt'
pid, session, sc, fresh = connect(W + '/flirt/loader/_cam_probe.js', tag='cam')
wait_stable(sc, tag='cam')

SPEC = [
    {'name': 'CCameraControlStrategy', 'rva': 0x2AFDA60},
    {'name': 'CTutMoveCameraTo',       'rva': 0x2A27E08},
    {'name': 'CTutDefaultMapmode',     'rva': 0x2A28108},
    {'name': 'CMapModeDispatcher',     'rva': 0x293E020},
]
res = sc.exports_sync.scan(SPEC)
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 定位摄像机相关对象的实例与内存布局')
A('方法       : 用虚表指针的 8 字节小端 pattern 扫全部 rw- 区域')
A('完整性     : 全量输出, 不抽样')
A('')
for sp in SPEC:
    name, rva = sp['name'], sp['rva']
    r = res.get(name) or {}
    A('%-26s rva=%#010x 实例命中=%s' % (name, rva, r.get('hits')))
    for h in (r.get('sample') or []):
        A('     %s  (所在区域 %d 字节)' % (h['addr'], h['size']))
A('')

allhit = []
for sp in SPEC:
    r = res.get(sp['name']) or {}
    for h in (r.get('sample') or []):
        allhit.append((sp['name'], h['addr']))

A('=== 前几个实例的 0x100 字节指针场与浮点场(全量) ===')
for name, addr in allhit[:6]:
    d = sc.exports_sync.dump(addr, 0x100)
    A('')
    A('### %s @ %s' % (name, addr))
    A('  -- 指针(偏移:值) --')
    for e in d['ptrs']:
        if e['v'] not in ('0x0',):
            A('    +%#04x -> %s' % (e['off'], e['v']))
    A('  -- 浮点 --')
    for e in d['floats']:
        f = e['f']
        if f is None: continue
        if abs(f) > 1e-6 and abs(f) < 1e7:
            A('    +%#04x = %r' % (e['off'], f))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)))
print('')
for sp in SPEC:
    r = res.get(sp['name']) or {}
    print('%-26s 命中 %s' % (sp['name'], r.get('hits')))
    for h in (r.get('sample') or [])[:4]:
        print('      %s' % h['addr'])
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
