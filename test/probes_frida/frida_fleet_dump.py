import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = open(W + '/flirt/loader/_fleet_dump.js', encoding='utf-8').read()
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
d = sc.exports_sync.dumpOne(0)
print('=== 首个有舰队的 CCountry ===')
print('  CCountry* = %s  索引字段(+0x08) = %s' % (d.get('country'), d.get('countryIdxField')))
print('  国家名(+0x10) = %r' % d.get('countryName'))
print('  CFleet* = %s' % d.get('fleetPtr'))
print('')
print('=== CFleet 对象前 0x130 字节 ===')
h = d.get('hex') or ''
for off in range(0, 0x130, 16):
    seg = h[off*2:(off+16)*2]
    pairs = [seg[i:i+4] for i in range(0, 32, 4)]
    q = int.from_bytes(bytes.fromhex(seg), 'little')
    print('  +0x%03X  %s   qword=%#018x' % (off, ' '.join(pairs), q))
print('')
s = sc.exports_sync.tagScan()
print('=== 所有 CFleet 的 +0x08 低4字节 分布 ===')
print('  %s' % s['lows'])
print('  +0x0C 去重数 = %s / 总数 %s' % (s['highsN'], s['n']))
print('')
print('=== 样本 (国家索引, +0x08, +0x0C, +0xA8, +0xB0, *(void**)(+0xA8)) ===')
for x in s['sample']:
    print('   %s' % (x,))
try: frida.kill(pid)
except Exception: pass