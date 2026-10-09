import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_st335.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 26:
    try: e.install(); break
    except Exception: time.sleep(1)
for i in range(25):
    time.sleep(1.5)
    try: n = e.n()
    except Exception: print('  失效'); break
    if n >= 300: break
n = e.n()
print('进入抵抗系统的州数 = %d  (原为 446)' % n)
ids = set(int(x) for x in e.ids().split(',') if x.strip())
for p in [1, 3, 335, 334, 336]:
    print('  州 %-4d %s' % (p, '在列表' if p in ids else '★ 被排除'))
