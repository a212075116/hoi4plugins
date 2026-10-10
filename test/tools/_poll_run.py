import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_poll.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
last = 0
for i in range(45):
    time.sleep(3)
    c = e.calls()
    if c != last:
        print('  %5.1fs  calls=%d   %s' % (time.time()-t0, c, e.poll()))
        last = c
    if c > 400 and i > 14:
        break
print('--- 继续观测 30 秒看 tag 是否变化 ---')
for i in range(10):
    time.sleep(3)
    print('  %5.1fs  %s' % (time.time()-t0, e.poll()))
