import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_arm2.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
for i in range(45):
    time.sleep(3)
    if i % 5 == 4 or e.armed():
        print('  %ds calls=%d armed=%s  %s' % ((i+1)*3, e.calls(), e.armed(), e.state()))
    if e.armed():
        d = e.dump()
        if d != '(none)':
            print('  *** 捕获写入 ***'); print(d); break
print('最终: calls=%d armed=%s  %s' % (e.calls(), e.armed(), e.state()))
print(e.dump())
