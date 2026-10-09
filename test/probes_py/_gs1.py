import sys, json, time
sys.path.insert(0, 'flirt/loader')
from frida_host import connect
pid, session, sc, fresh = connect('flirt/loader/_gs1.js', tag='gs1')
time.sleep(0.5)
print(json.dumps(sc.exports_sync.gs(), indent=1, ensure_ascii=False), flush=True)
session.detach()
print('[游戏保持运行 pid=%s]' % pid, flush=True)
