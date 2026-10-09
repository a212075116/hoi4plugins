import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
JS = open(W + '/flirt/loader/_st.js', encoding='utf-8').read()
pid = frida.spawn([W + '/hoi4.exe', '-gdpr-compliant', '-quickstart', '-nolauncher'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time()
while time.time() - t0 < 300:
    try: r = sc.exports_sync.st()
    except Exception as e: r = {'ok': False, 'why': str(e)}
    print('  t=%3.0fs  %s' % (time.time() - t0, r), flush=True)
    time.sleep(15)
try: frida.kill(pid)
except Exception: pass