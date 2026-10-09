import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
JS = open(W + '/flirt/loader/_diag2.js', encoding='utf-8').read()
pid = frida.spawn([W + '/hoi4.exe', '-gdpr-compliant', '-quickstart', '-nolauncher'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time()
while time.time() - t0 < 200:
    try: st = sc.exports_sync.st()
    except Exception as e: st = {'ok': False}
    if st.get('ok') and (st.get('countries') or 0) > 50: break
    time.sleep(2)
print('[gamestate] %.0fs %s' % (time.time() - t0, st), flush=True)
time.sleep(120)
print('[开始扫描虚表]', flush=True)
t1 = time.time()
r = sc.exports_sync.scan()
print('[扫描耗时 %.0fs]' % (time.time() - t1), flush=True)
print('')
print('=== 原版环境 (quickstart, 无 mod) 全堆虚表命中数 ===')
for k in ('CProvince', 'CState', 'CCountry', 'CCharacter', 'CFleet'):
    print('   %-12s = %s' % (k, r.get(k)))
try: frida.kill(pid)
except Exception: pass