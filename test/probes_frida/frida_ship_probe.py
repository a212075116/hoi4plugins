import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_fleet_ship_probe.txt'
JS = open(W + '/flirt/loader/_ship_probe.js', encoding='utf-8').read()
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
    else:
        stable += 1
    c = st.get('chi') or {}
    if c.get('fleets') and c.get('cands') and stable >= 4:
        print('[世界稳定]', flush=True); break
    time.sleep(5)
print('', flush=True)
print('[dumpChi] 用时 %.0fs' % (time.time()-t0), flush=True)
d = sc.exports_sync.dumpChi()
print('[dumpChi 返回 ok=%s err=%s]' % (d.get('ok'), d.get('err')), flush=True)
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 在 CFleet 内部找出装载 军舰(CShip) 与 特遣舰队(CTaskForce) 的容器')
A('靶子       : history/units/CHI_1936_naval_mtg.txt 里 Di 1 Jiandui 有 9 条船')
A('             Ninghai/Hairong/Haichen/Haichou/Zhaohe/Yingrui/Yu Chang/Chien kang/Tung An')
A('完整性     : 全量输出 CFleet 全部 0x130 字节 + 全部容器候选, 不抽样, 不过滤')
A('')
A('--- CHI 的 CFleet 全量 (%s 个) ---' % d.get('fleetCount'))
A('CHI CCountry* : %s   (数组索引 %s)' % (d.get('chiPtr'), d.get('idx')))
A('CGameState*   : %s' % d.get('gs'))
A('')
for f in d.get('fleets', []):
    A('  [%d] %s' % (f['i'], f['ptr']))
    A('      名字 (CFleet+0xE0/+0xF0/+0xF8) = %r' % f['name'])
    A('      完整 0x130 字节:')
    h = f['hex'] or ''
    for row in range(0, len(h), 32):
        o = row // 2
        A('        +0x%03x  %s' % (o, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
    A('')
    A('      容器候选 (对每个 8 字节对齐偏移 off 读 data=*(f+off), count=*(dword*)(f+off+0x0C), 两者合理即列出):')
    for c in f['cand']:
        A('        off=+0x%-4x data=%s count=%s' % (c['off'], c['data'], c['count']))
        for k, e in enumerate(c['elems']):
            A('             [%2d] %s' % (k, e))
    A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)))
print('')
for f in d.get('fleets', []):
    print('CHI 舰队 [%d] %s 名字=%r  容器候选=%d 个' % (f['i'], f['ptr'], f['name'], len(f['cand'])))
    for c in f['cand']:
        print('    +0x%-4x count=%-8s' % (c['off'], c['count']))
        for k, e in enumerate(c['elems'][:6]):
            print('        [%2d] %s' % (k, e))
try: frida.kill(pid)
except Exception: pass
