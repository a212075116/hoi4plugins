import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_judge.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
last = ''
for i in range(45):
    time.sleep(3)
    st = e.stats()
    if st != last:
        print('  %ds: %s' % ((i+1)*3, st)); last = st
    if 'tag0=' in st and int(st.split('tag0=')[1].split()[0]) > 0:
        print('  *** 出现 tag0 ***'); break
print('最终: ' + e.stats())
print('tag 分布: ' + e.tags())
