import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_CFleet_CTaskForce_容器下钻.txt'
JS = open(W + '/flirt/loader/_tf_probe.js', encoding='utf-8').read()
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
    if key != last:
        print('[状态 %.0fs] %s' % (time.time()-t0, key), flush=True); last = key; stable = 0
    else: stable += 1
    if (st.get('chi') or {}).get('fleets') and stable >= 4:
        print('[稳定]', flush=True); break
    time.sleep(5)
d = sc.exports_sync.dumpTF()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 从 CFleet 下钻到 CTaskForce, 找到装载军舰(CShip)的容器')
A('靶子       : CHI_1936_naval_mtg.txt 的 Di 1 Jiandui = 1 个 task_force + 9 条 ship')
A('完整性     : 全量输出, 不抽样, 不过滤')
A('')
A('--- 虚表名对照 (RVA -> 名字) ---')
A('  CShip_a=0x2957F28  CShip_b=0x2957F90')
A('  CTaskForce_a=0x2962F70 b=0x2963150 c=0x29631C0 d=0x2963208')
A('  CFleet_a=0x2962A18 b=0x2962A70')
A('')
A('--- CHI 的 CFleet (%s 个) ---' % d.get('fleetCount'))
A('  CGameState* = %s   CHI CCountry* = %s (索引 %s)' % (d.get('gs'), d.get('chiPtr'), d.get('idx')))
A('')
for f in d.get('fleets', []):
    A('  [舰队 %d] %s  名字=%r' % (f['i'], f['ptr'], f['name']))
    A('      CFleet+0xB8 (task_force 数组 data) = %s   CFleet+0xC4 (元素数) = %s' % (f['tfData'], f['tfCount']))
    for tf in f['tfs']:
        A('      [特遣舰队 %d] %s  虚表=%s' % (tf['i'], tf['ptr'], tf['vt']))
        A('          完整 0x200 字节:')
        h = tf['hex'] or ''
        for row in range(0, len(h), 32):
            A('            +0x%03x  %s' % (row // 2, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
        A('          容器候选:')
        for c in tf['cand']:
            A('            off=+0x%-4x data=%s count=%s' % (c['off'], c['data'], c['count']))
            for k, e in enumerate(c['elems']):
                A('                 [%2d] %s' % (k, e))
        A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for f in d.get('fleets', []):
    print('舰队 [%d] %s 名字=%r  task_force 数=%s (data=%s)' % (f['i'], f['ptr'], f['name'], f['tfCount'], f['tfData']))
    for tf in f['tfs']:
        print('   特遣舰队 [%d] %s 虚表=%s' % (tf['i'], tf['ptr'], tf['vt']))
        for c in tf['cand']:
            print('      +0x%-4x count=%-6s %s' % (c['off'], c['count'], c['elems'][:4]))
try: frida.kill(pid)
except Exception: pass
