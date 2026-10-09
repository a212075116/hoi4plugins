import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
# 手动加 -debug
fh.ARGS = [fh.ARGS[0], '-gdpr-compliant', '-start_tag=ABY', '-nolauncher', '-debug']
print('ARGS = ' + str(fh.ARGS))
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_launch.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 20:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(22):
    time.sleep(2)
    if e.n() > 0 and i > 12: break
print('捕获数 = %d' % e.n())
print(e.dump())
