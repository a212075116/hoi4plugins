import sys, time, importlib.util, os
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 120:
    if e.ready().get('ok'): break
    time.sleep(0.5)
print('就绪 %.1f 秒' % (time.time()-t0))
print('执行 crashme ...')
try:
    print(str(e.exec('crashme', []))[:200])
except Exception as ex:
    print('(进程已崩, 预期) %s' % str(ex)[:120])
