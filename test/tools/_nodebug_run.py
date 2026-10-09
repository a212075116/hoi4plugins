import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
fh.ARGS = [fh.ARGS[0], '-gdpr-compliant', '-start_tag=ABY', '-nolauncher', '-debug']
print('ARGS = ' + str(fh.ARGS))
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_nodebug.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 20:
    try: print('install: %s' % e.install()); break
    except Exception: time.sleep(1)
last = ''
for i in range(22):
    time.sleep(2)
    st = e.state()
    if st != last: print('  %5.1fs %s' % (time.time()-t0, st)); last = st
print('最终: ' + e.state())
print(e.dump())
