import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_fn.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.install())
print('calls 初始: %d' % e.calls())
# 等到每日更新被调用 (说明已进地图且游戏在跑)
for i in range(60):
    time.sleep(3)
    c = e.calls()
    if c > 0:
        print('  %ds: calls=%d' % ((i+1)*3, c))
        break
else:
    print('  90s 内未调用')
print(e.dump())
