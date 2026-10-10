import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_cmpocc.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 28:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(25):
    time.sleep(1.5)
    try: c = e.calls()
    except Exception: print('  失效'); break
    if c >= 446: break
print('calls=%d 用时 %.1fs' % (e.calls(), time.time()-t0))
time.sleep(4)
print(e.cmp())
