import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_gamedate.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('install: %s' % e.install(), flush=True)
print('观察 15 秒 (游戏速度 3)...', flush=True)
time.sleep(15)
print(e.stat(), flush=True)
fh.detach(session)
