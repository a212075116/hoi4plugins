import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/effect/effect_registry_probe.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
print('=== 构造并注册 effect (token id 70279) ===')
print(e.install(70279))
