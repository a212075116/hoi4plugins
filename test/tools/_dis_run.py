import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
print('ARGS = ' + str(fh.ARGS))
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dis.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 25:
    try: e.base(); break
    except Exception: time.sleep(1)
print('=== 0xffddf0 起 45 条 (有占领数据时的处理) ===')
print(e.dis(0xffddf0, 45))
