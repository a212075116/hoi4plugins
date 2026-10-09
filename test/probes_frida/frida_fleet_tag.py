import frida, time, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_fleet_tag.js', encoding='utf-8').read()
pid = frida.spawn([W + '/hoi4.exe', '-gdpr-compliant', '-start_tag=CHI', '-nolauncher'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time()
while time.time() - t0 < 240:
    try:
        if 'Launching SINGLEPLAYER-game' in open(LOG, encoding='utf-8', errors='ignore').read():
            print('[已进入游戏] %.0fs' % (time.time()-t0), flush=True); break
    except Exception: pass
    time.sleep(1)
else:
    print('[未检测到 Launching]', flush=True)
print('[等待 40s 让世界完全建立]', flush=True)
time.sleep(40)
r = sc.exports_sync.dump()
print('')
print('CGameState* = %s' % r['gs'])
print('国家数      = %s' % r['countries'])
print('有非空指针的国家数 = %s' % r['nl'])
print('舰队元素总计数     = %s' % r['tot'])
print('')
if r['rows']:
    print('=== 有舰队的国家 (最多 60) ===')
    for x in r['rows'][:60]:
        print('  #%-4d CCountry=%-18s arr=%-18s num=%s' % (x['ci'], x['c'], x['arr'], x['num']))
else:
    print('(没有任何国家有舰队元素)')
try: frida.kill(pid)
except Exception: pass