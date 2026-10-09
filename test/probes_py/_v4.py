import sys, json, time
sys.path.insert(0, 'flirt/loader')
from frida_host import connect
print('attach ...', flush=True)
pid, session, sc, fresh = connect('flirt/loader/_cam4.js', tag='cam4')
time.sleep(1)
r = sc.exports_sync.verify()
print(json.dumps(r, indent=1, ensure_ascii=False), flush=True)
session.detach()
print('[游戏保持运行 pid=%s]' % pid, flush=True)
