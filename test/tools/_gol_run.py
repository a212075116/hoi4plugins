import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
print('=== spawn (ABY) + hook GetOccupationLaw ===')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_gol.js', force_spawn=True, wait=False)
print('pid=%s' % pid)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try:
        print('  install: %s' % e.install()); break
    except Exception:
        time.sleep(1)
last = ''
for i in range(60):
    time.sleep(3)
    try: st = e.stats()
    except Exception as ex: print('  失效'); break
    if st != last:
        print('  %ds: %s' % ((i+1)*3, st)); last = st
    if 'nulls=0' not in st and int(st.split('nulls=')[1]) >= 1:
        print('  *** 命中 ***'); break
print()
print(e.dump())
