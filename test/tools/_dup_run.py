import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dup.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 30:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
last = ''
for i in range(50):
    time.sleep(1)
    try: st = e.stats()
    except Exception: print('  失效'); break
    if st != last:
        print('  %5.1fs %s' % (time.time()-t0, st)); last = st
    if 'calls=446' in st:
        time.sleep(3)
        print('  3 秒后: ' + e.stats())
        break
print('最终 ' + e.stats())
print(e.dups())
