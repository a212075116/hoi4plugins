import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_tagtab3.js', encoding='utf-8').read()
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
print('CGameState+0x358 ptr=%s n=%s' % (r['ptr'], r['n']))
print('')
print('=== 前 10 项 ===')
for x in r['first']:
    print('  [%2d] tag=%-6r raw=%#010x  +0x10=%s +0x18=%s' % (x['i'], x['tag'], x['raw'], x['s16'], x['s24']))
print('')
print('=== CCountry #0..#9 与同索引 tag 对照 ===')
for x in r['cc']:
    print('  #%-3s idx(+8)=%-4s tag@sameIdx=%-6r 名字=%r' % (x['ci'], x['idx'], x['tagAtSameIdx'], x['name']))
try: frida.kill(pid)
except Exception: pass