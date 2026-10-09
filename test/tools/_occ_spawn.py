import sys, time, importlib.util, os
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
print('ARGS = ' + str(fh.ARGS))
print('=== spawn (ABY) ===')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_occ.js', force_spawn=True, wait=False)
print('pid=%s' % pid)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try:
        print('  %.1fs install: %s' % (time.time()-t0, e.install()))
        break
    except Exception as ex:
        time.sleep(1)
else:
    print('  模块未就绪')
print('=== 监视 (最长 150s) ===')
last = ''
for i in range(50):
    time.sleep(3)
    try:
        st = e.stats()
    except Exception as ex:
        print('  脚本失效: %s' % str(ex)[:60]); break
    if st != last:
        print('  %ds: %s' % ((i+1)*3, st))
        last = st
    if 'matched=0' not in st:
        print('  *** 命中! ***')
        try: print(e.dump())
        except Exception as ex: print('  dump: %s' % str(ex)[:80])
        break
print('最终: ' + last)
