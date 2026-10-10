import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_occ.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.install())
t0 = time.time()
seen = 0
while time.time() - t0 < 240:
    time.sleep(3)
    try:
        n = e.hitCount()
    except Exception as ex:
        print('  脚本失效: %s' % str(ex)[:60]); break
    if n != seen:
        print('  %.0fs: hits=%d' % (time.time()-t0, n))
        seen = n
    if n >= 2:
        print('  已收集足够样本')
        break
print('最终 hits=%d, 用时 %.0fs' % (seen, time.time()-t0))
