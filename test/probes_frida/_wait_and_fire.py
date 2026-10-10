import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
last = None
ok = False
while time.time() - t0 < 180:
    st = e.ready()
    s = str(st)
    if s != last:
        print('%6.1fs  %s' % (time.time()-t0, s)); sys.stdout.flush()
        last = s
    if st.get('ok'):
        ok = True; break
    time.sleep(0.5)
if not ok:
    print('=> 未进地图'); sys.exit(1)
print('=> 进地图, 用时 %.1f 秒' % (time.time()-t0))
print('摄像机 %.2f' % e.camHeight())
print(e.exec('event', ['camtest.1'])[:130])
time.sleep(1.5)
print('摄像机之后 %.2f' % e.camHeight())
print()
print('=== efftip ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'efftip' in l: print('  ' + l)
