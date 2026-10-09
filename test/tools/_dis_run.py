import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dis.js', force_spawn=False, wait=False)
time.sleep(0.5)
e = sc.exports_sync
for st in (0xf9c5a0, 0xf9c5b0, 0xf9c680, 0xf9c6d0):
    r = e.dis(st, 20)
    print('--- 起点 %#x ---' % st)
    print(r)
    print()
