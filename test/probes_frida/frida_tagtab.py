import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_tagtab.js', encoding='utf-8').read()
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
time.sleep(60)
r = sc.exports_sync.probe()
print('CGameState = %s' % r['gs'])
print('')
print('=== CGameState + 0x358 数组 (32 字节/项) ===')
print('  ptr=%s  n=%s' % (r['arr358']['ptr'], r['arr358']['n']))
for it in r['items']:
    print('  [%2d] q0=%s d8=%s d12=%s' % (it['i'], it['q0'], it['d8'], it['d12']))
    print('       ascii=|%s|' % it['asc'])
print('')
for cc in r['ccScan']:
    print('=== CCountry #%d  %s  名字=%r ===' % (cc['ci'], cc['ptr'], cc['name']))
    for L in cc['lines']:
        print('  ' + L)
    print('')
try: frida.kill(pid)
except Exception: pass