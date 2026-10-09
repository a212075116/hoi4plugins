import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
JS = open(W + '/flirt/loader/_diag3.js', encoding='utf-8').read()
pid = frida.spawn([W + '/hoi4.exe', '-gdpr-compliant', '-quickstart', '-nolauncher'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time()
last = None
while time.time() - t0 < 250:
    try: st = sc.exports_sync.st()
    except Exception as e: st = {'ok': False}
    if st.get('ok'):
        key = (st.get('countries'), st.get('chars'))
        if key != last: print('  %s (%.0fs)' % (key, time.time()-t0), flush=True); last = key
    time.sleep(5)
print('[等 150s 让世界完全就绪]', flush=True)
time.sleep(150)
print('[扫描]', flush=True)
t1 = time.time()
r = sc.exports_sync.scan()
print('[耗时 %.0fs]' % (time.time()-t1), flush=True)
print('')
print('=== 原版 1936 一局 (quickstart) 全堆虚表命中 ===')
for k in ('CShip_a', 'CShip_b', 'CTaskForce_a', 'CFleet_a', 'CFleet_b'):
    v = r.get(k, {})
    print('   %-14s 命中 %-8s 样本 %s' % (k, v.get('n'), v.get('samples', [])[:3]))
try: frida.kill(pid)
except Exception: pass