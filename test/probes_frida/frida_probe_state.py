# frida_probe_state.py -- 对照探针: 判断游戏是否真的在一局游戏里
#
# 对照项:
#   CCharacter 管理器  CGameState + 0x6A8 (mod 环境实测 2451 项)
#   CProvince 数组     CGameState + 0x2B0
#   CState 数组        CGameState + 0x2C8
#   CCountry 数组      CGameState + 0x310
#   CFleet 数组        CCountry + 0x278 / 数量 +0x284
# 如果 CCharacter 也是 0, 说明游戏根本没进一局(停主菜单)。
import frida, time, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
SAVE = os.environ.get('FRIDA_START_SAVE', '')
JS = open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/flirt/loader/_probe_state.js', encoding='utf-8').read()
args = [EXE, '-gdpr-compliant']
if SAVE: args += ['-start_save=' + SAVE, '-nolauncher', '-allowoldsave']
else: args += ['-continuelastsave']
print('[启动参数] %s' % ' '.join(args), flush=True)
pid = frida.spawn(args)
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time(); last = None
while time.time() - t0 < 200:
    try: st = sc.exports_sync.status()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'):
        key = (st.get('provinces'), st.get('countries'), st.get('chars'))
        if key != last: print('  %s (%.0fs)' % (key, time.time()-t0), flush=True); last = key
        if st.get('countries', 0) > 50: break
    time.sleep(1)
time.sleep(20)
r = sc.exports_sync.dump()
print('')
for k in ('gs', 'provinces', 'states', 'countries', 'charsNum', 'charsData', 'charsLive'):
    print('  %-12s = %s' % (k, r.get(k)))
print('')
tot = 0
ct = 0
for x in r.get('rows', []):
    if x.get('num'):
        tot += x['num']; ct += 1
        if ct <= 8: print('  国家#%d  CCountry=%s  舰队数=%s  数组=%s' % (x['ci'], x['c'], x['num'], x.get('arr')))
print('  有舰队的国家数 = %d, 舰队总数 = %d' % (ct, tot))
print('')
print('  === 扫堆找 CFleet 虚表 ===')
sc2 = sc.exports_sync.scanVt()
print('  命中: %s' % sc2)
try: frida.kill(pid)
except Exception: pass