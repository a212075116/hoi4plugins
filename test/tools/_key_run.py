import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_key.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(45):
    time.sleep(3)
    if e.calls() > 5 and i > 3:
        print('  %ds: calls=%d' % ((i+1)*3, e.calls())); break
print(e.dump())
