import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_wpt.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print(e.api(), flush=True)
print(e.install(0x478), flush=True)
time.sleep(8)
print('命中: %d' % e.n(), flush=True)
print(e.hits(), flush=True)
fh.detach(session)
