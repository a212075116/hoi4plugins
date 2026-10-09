import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 20:
    try: e.ready(); break
    except Exception: time.sleep(1)
print('=== 全局找 500 (i32) ===', flush=True)
r = e.exact(500)
print(r, flush=True)
