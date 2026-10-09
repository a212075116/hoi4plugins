import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_watch.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
print('等待第一次调用...')
while time.time() - t0 < 90:
    time.sleep(1)
    if e.calls() > 0: break
print('calls=%d' % e.calls())
print(e.watch())
for i in range(30):
    time.sleep(3)
    d = e.dump()
    if d != '(none)':
        print('  %ds 捕获到写入:' % ((i+1)*3))
        print(d); break
print('最终 tag=' + e.targetTag())
print(e.dump())
