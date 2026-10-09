import frida, time, json
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_gs_probe.js', encoding='utf-8').read()
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
print('=== CGameState 候选容器 ===')
for c in r['candidates']:
    print('  +0x%03X ptr=%-20s n=%-6s' % (c['off'], c['ptr'], c['n']))
    if c.get('cstrs'):
        print('        字符串样本: %s' % c['cstrs'])
print('')
print('=== CCountry 前 6 个的候选字段 ===')
for c in r['ccs']:
    print('  #%s ptr=%s idx(+8)=%s' % (c['ci'], c['p'], c['idx']))
    print('     +0x10 ptr=%s  asCString=%r' % (c['q10'], c['s10']))
    print('     +0x30 asCString=%r   +0x50 asCString=%r' % (c['q30'], c['q50']))
try: frida.kill(pid)
except Exception: pass