# -*- coding: utf-8 -*-
import sys, json, time, os
sys.path.insert(0, 'flirt/loader')
from frida_host import connect

# 先等游戏进入对局
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
t0 = time.time()
while time.time() - t0 < 180:
    try:
        if 'Launching SINGLEPLAYER-game' in open(LOG, encoding='utf-8', errors='ignore').read():
            print('[进入对局] %.0fs' % (time.time() - t0), flush=True)
            break
    except Exception:
        pass
    time.sleep(2)
else:
    print('[警告] 180s 内未见进入对局标记, 继续尝试 attach', flush=True)

time.sleep(6)
pid, session, sc, fresh = connect('flirt/loader/_cam5.js', tag='cam5')
print('已 attach pid=%s' % pid, flush=True)
print('', flush=True)
print('>>> 现在开始 70 秒监视: 请【滚轮拉到最近 -> 停3秒 -> 滚轮拉到最远 -> 停3秒】<<<', flush=True)
print('', flush=True)

SECONDS = 70
GAP = 0.5   # 采样间隔, 1 秒 2 次
t1 = time.time()
rows = []
while time.time() - t1 < SECONDS:
    r = sc.exports_sync.sample()
    if r.get('ok'):
        rows.append((round(time.time() - t1, 3), r['s']))
    time.sleep(GAP)
print('采样点数 =', len(rows), ' 用时 %.1fs' % (time.time() - t1), flush=True)
if not rows:
    print('无数据'); sys.exit(1)
offs = [x[0] for x in rows[0][1]['f']]
varying = []
for k, off in enumerate(offs):
    vals = [row[1]['f'][k][1] for row in rows]
    uniq = set('%.4f' % v for v in vals)
    if len(uniq) > 1:
        varying.append((off, len(uniq), min(vals), max(vals), max(vals) - min(vals)))
print('', flush=True)
print('=== 有变化的 float (按变化幅度排序) ===', flush=True)
print('%-9s %-8s %-14s %-14s %-12s' % ('偏移', '不同值', '最小', '最大', '幅度'), flush=True)
for off, c, lo, hi, amp in sorted(varying, key=lambda t: -t[4]):
    print('+0x%-6x %-8d %-14.4f %-14.4f %-12.4f' % (off, c, lo, hi, amp), flush=True)
print('', flush=True)
print('=== 全程不变的关键偏移 ===', flush=True)
for k, off in enumerate(offs):
    if off in (0x6C8, 0x6CC, 0x6D0, 0x6D4, 0x6F0, 0x6F4, 0x6F8, 0x6FC):
        v = rows[0][1]['f'][k]
        print('  +0x%-5x float=%-16.4f int=%d' % (off, v[1], v[2]), flush=True)
with open('reports/camera_monitor2.csv', 'w', encoding='utf-8') as fp:
    fp.write('t,off,float,int\n')
    for t, s in rows:
        for off, fv, iv in s['f']:
            fp.write('%s,%#x,%.6f,%d\n' % (t, off, fv, iv))
print('', flush=True)
print('[写出] reports/camera_monitor2.csv', flush=True)
session.detach()
print('[游戏保持运行 pid=%s]' % pid, flush=True)
