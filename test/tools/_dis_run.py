import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dis.js', force_spawn=False, wait=False)
time.sleep(0.5)
e = sc.exports_sync
print('=== 0x1810c0 起 30 条 (上层调用者) ===')
print(e.dis(0x1810c0, 30))
print()
print('=== 0x175b00 起 25 条 (本函数更前面, 找入口与判断) ===')
print(e.dis(0x175b00, 25))
