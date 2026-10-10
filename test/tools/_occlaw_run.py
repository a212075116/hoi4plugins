import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
print('=== spawn (ABY) + hook 取占领数据 ===')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_occlaw.js', force_spawn=True, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 60:
    try: print('  install: %s' % e.install()); break
    except Exception: time.sleep(1)
last = ''
for i in range(50):
    time.sleep(3)
    try: st = e.stats()
    except Exception as ex: print('  失效: %s' % str(ex)[:50]); break
    if st != last:
        print('  %ds: %s' % ((i+1)*3, st)); last = st
    if 'null=0' not in st and int(st.split('null=')[1]) > 0:
        print('  *** 捕获到 NULL 返回 ***' )
        print(e.dump()); break
print('最终 ' + last)
print(e.dump())
