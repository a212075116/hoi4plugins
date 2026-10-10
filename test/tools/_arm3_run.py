import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_arm3.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(60):
    time.sleep(2)
    try:
        c = e.calls(); a = e.armed(); c0 = e.count0()
    except Exception as ex:
        print('  脚本失效: %s' % str(ex)[:60]); break
    print('  %5.1fs calls=%-4d armed=%-5s %s' % (time.time()-t0, c, a, c0))
    d = e.dump()
    if d != '(none)':
        print('  *** 捕获到写入 ***')
        print(d)
        break
print()
print('最终: %s' % e.count0())
print(e.dump())
