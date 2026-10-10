import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_arm5.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(50):
    time.sleep(2)
    try: c = e.calls(); p = e.pages()
    except Exception: print('  失效'); break
    if c > 0 and i % 3 == 0:
        print('  %5.1fs calls=%d pages=%d' % (time.time()-t0, c, p))
    d = e.dump()
    if d != '(none)':
        print('  *** 捕获 ***'); print(d); break
    if c >= 446 and i > 25: break
print('最终 calls=%d pages=%d' % (e.calls(), e.pages()))
print(e.dump())
