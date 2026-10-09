# -*- coding: utf-8 -*-
import sys, json, time
sys.path.insert(0, 'flirt/loader')
from frida_host import connect
pid, session, sc, fresh = connect('flirt/loader/_w1.js', tag='w1')
time.sleep(0.5)
a = sc.exports_sync.rd()
print('改前:', json.dumps(a.get('s'), ensure_ascii=False), flush=True)
print('', flush=True)
TARGET = 100.0
for off in (0x69C, 0x678):
    r = sc.exports_sync.wf(off, TARGET)
    print('写 +0x%X = %.1f -> %s' % (off, TARGET, 'ok' if r.get('ok') else r.get('err')), flush=True)
print('', flush=True)
for i in range(8):
    time.sleep(0.5)
    s = sc.exports_sync.rd().get('s')
    if not s: break
    print('  #%-2d 0x678=%-12.4f 0x69C=%-12.4f 0x684=%-12.4f 0x6FC=%-12.4f 0x6D0=%-5d 0x6D4=%-6d' % (
        i+1, s['f678'], s['f69c'], s['f684'], s['f6fc'], s['i6d0'], s['i6d4']), flush=True)
session.detach()
print('', flush=True)
print('[游戏保持运行 pid=%s]' % pid, flush=True)
