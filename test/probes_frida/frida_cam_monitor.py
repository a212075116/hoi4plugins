# -*- coding: utf-8 -*-
import sys, json, time, os
sys.path.insert(0, 'flirt/loader')
from frida_host import connect
OUT = 'reports/camera_monitor.csv'
SECONDS = 45
GAP = 0.5   # 采样间隔, 1 秒 2 次
pid, session, sc, fresh = connect('flirt/loader/_cam5.js', tag='cam5')
t0 = time.time()
rows = []
n = 0
while time.time() - t0 < SECONDS:
    r = sc.exports_sync.sample()
    if r.get('ok'):
        rows.append((round(time.time() - t0, 3), r['s']))
        n += 1
    time.sleep(GAP)
print('采样点数 =', n, ' 用时 %.1fs' % (time.time() - t0), flush=True)
if not rows:
    print('无数据:', r); sys.exit(1)
offs = [x[0] for x in rows[0][1]['f']]
# 找出每个偏移上出现过的不同值个数
varying = []
for k, off in enumerate(offs):
    vals = [row[1]['f'][k][1] for row in rows]
    uniq = set('%.4f' % v for v in vals)
    if len(uniq) > 1:
        varying.append((off, len(uniq), min(vals), max(vals)))
print('', flush=True)
print('=== 在 %.0f 秒内发生变化(candidate) 的 float 偏移 ===' % SECONDS, flush=True)
print('%-10s %-8s %-16s %-16s' % ('偏移', '不同值数', '最小', '最大'), flush=True)
for off, c, lo, hi in varying:
    print('+0x%-7x %-8d %-16.4f %-16.4f' % (off, c, lo, hi), flush=True)
print('', flush=True)
print('=== 静止不变的关键偏移 ===', flush=True)
for k, off in enumerate(offs):
    if off in (0x6C8, 0x6CC, 0x6D0, 0x6D4, 0x6F0, 0x6F4, 0x6F8, 0x6FC):
        vals = [row[1]['f'][k][1] for row in rows]
        print('  +0x%-5x float=%-16.4f int=%d' % (off, vals[0], rows[0][1]['f'][k][2]), flush=True)
with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write('t,off,float,int\n')
    for t, s in rows:
        for off, fv, iv in s['f']:
            fp.write('%s,%#x,%.6f,%d\n' % (t, off, fv, iv))
print('', flush=True)
print('[写出] %s' % OUT, flush=True)
session.detach()
print('[游戏保持运行 pid=%s]' % pid, flush=True)
