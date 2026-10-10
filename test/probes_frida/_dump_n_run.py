import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dump_n.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
print('=== +0x28 == 1 的三个样例 ===')
print(e.dumpN(1))
print('=== +0x28 == 2 的样例 ===')
print(e.dumpN(2))
