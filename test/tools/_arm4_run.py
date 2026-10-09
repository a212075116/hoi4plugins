import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_arm4.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(50):
    time.sleep(2)
    try: c = e.calls(); a = e.armed(); p = e.pages(); c0 = e.count0()
    except Exception as ex: print('  失效'); break
    if a:
        print('  %5.1fs calls=%d armed=%s pages=%d %s' % (time.time()-t0, c, a, p, c0))
    d = e.dump()
    if d != '(none)':
        print('  *** 捕获 ***'); print(d); break
    if a and i > 20: break
print('最终 pages=%d %s' % (e.pages(), e.count0()))
print(e.dump())
