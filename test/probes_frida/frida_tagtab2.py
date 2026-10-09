import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_tagtab2.js', encoding='utf-8').read()
pid = frida.spawn([W + '/hoi4.exe', '-gdpr-compliant', '-start_tag=CHI', '-nolauncher'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
t0 = time.time()
while time.time() - t0 < 240:
    try:
        if 'Launching SINGLEPLAYER-game' in open(LOG, encoding='utf-8', errors='ignore').read(): print('[进入游戏] %.0fs' % (time.time()-t0), flush=True); break
    except Exception: pass
    time.sleep(1)
time.sleep(55)
r = sc.exports_sync.go()
for key in ('t358', 't328', 't340', 't370'):
    a = r.get(key)
    if not a: continue
    print('=== %s  ptr=%s  n=%s ===' % (a['label'], a['ptr'], a['n']))
    for it in a['items']:
        print('  [%2d] dw=%s  |%s|' % (it['i'], it['dw'], it['asc']))
    print('')
try: frida.kill(pid)
except Exception: pass