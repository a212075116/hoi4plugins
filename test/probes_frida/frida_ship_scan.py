import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CShip_全堆虚表扫描.txt'
JS = open(W + '/flirt/loader/_ship_scan.js', encoding='utf-8').read()
try: os.remove(LOG)
except Exception: pass
args = [W + '/hoi4.exe', '-gdpr-compliant', '-start_tag=CHI', '-nolauncher']
print('[启动] %s' % ' '.join(args), flush=True)
pid = frida.spawn(args)
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
t0 = time.time()
while time.time() - t0 < 240:
    try:
        if 'Launching SINGLEPLAYER-game' in open(LOG, encoding='utf-8', errors='ignore').read():
            print('[进入游戏] %.0fs' % (time.time()-t0), flush=True); break
    except Exception: pass
    time.sleep(1)
last = None; stable = 0
while time.time() - t0 < 320:
    try: st = sc.exports_sync.st()
    except Exception as e: st = {'ok': False, 'err': str(e)}
    key = json.dumps(st, ensure_ascii=False, sort_keys=True)
    if key != last: print('[状态 %.0fs] %s' % (time.time()-t0, key), flush=True); last = key; stable = 0
    else: stable += 1
    if (st.get('chi') or {}).get('fleets') and stable >= 4: print('[稳定]', flush=True); break
    time.sleep(5)
print('[内存区域] %s' % sc.exports_sync.info(), flush=True)
print('[扫描中]', flush=True)
r = sc.exports_sync.scanAll()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 全堆统计 CShip / CTaskForce / CFleet 的真实实例数')
A('完整性     : 全量统计, 不抽样')
A('')
A('内存区域: %s' % sc.exports_sync.info())
A('扫描耗时: %s ms' % r.get('_ms'))
A('')
for k in ('CShip_a', 'CShip_b', 'CTaskForce_a', 'CFleet_a'):
    v = r.get(k, {})
    A('%-14s 命中 %-8s 样本 %s' % (k, v.get('n'), v.get('samples', [])))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s' % OUT, flush=True)
for k in ('CShip_a', 'CShip_b', 'CTaskForce_a', 'CFleet_a'):
    print('   %-14s %s' % (k, r.get(k, {}).get('n')))
print('样本 CShip_a:', r.get('CShip_a', {}).get('samples', [])[:5])
try: frida.kill(pid)
except Exception: pass
