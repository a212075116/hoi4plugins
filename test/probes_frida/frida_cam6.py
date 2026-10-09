# -*- coding: utf-8 -*-
import sys, json, time
sys.path.insert(0, 'flirt/loader')
from frida_host import connect
pid, session, sc, fresh = connect('flirt/loader/_cam6.js', tag='cam6')
time.sleep(0.5)
a = sc.exports_sync.rd()
print('改前:', json.dumps(a.get('s'), ensure_ascii=False), flush=True)
# 试改高度候选 +0x69C -> 200
for off, val in [(0x69C, 200.0), (0x678, 200.0)]:
    r = sc.exports_sync.wf(off, val)
    print('写入 +0x%X = %s -> %s' % (off, val, 'ok' if r.get('ok') else r.get('err')), flush=True)
    time.sleep(1.5)
    s = sc.exports_sync.rd().get('s')
    print('   1.5s 后:', json.dumps(s, ensure_ascii=False), flush=True)
    time.sleep(2)
    s2 = sc.exports_sync.rd().get('s')
    print('   3.5s 后:', json.dumps(s2, ensure_ascii=False), flush=True)
session.detach()
print('[游戏保持运行 pid=%s]' % pid, flush=True)
