import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_9条军舰_反向归属验证.txt'
JS = open(W + '/flirt/loader/_ship_back.js', encoding='utf-8').read()
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
d = sc.exports_sync.hunt()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 从全堆 1356 个 CShip 中按名字锁定 CHI 的 9 条军舰, 并找出每条船指向的 CTaskForce/CFleet')
A('靶子       : CHI_1936_naval_mtg.txt 的 Di 1 Jiandui 的 9 条 ship')
A('完整性     : 全量输出, 不抽样, 不过滤')
A('')
A('CShip 总数 = %s   扫描耗时 = %s ms   匹配耗时 = %s ms' % (d.get('total'), d.get('scanMs'), d.get('matchMs')))
A('按名字命中的 CHI 军舰数 = %s' % len(d.get('found', [])))
A('')
TARGET = ['Ninghai', 'Hairong', 'Haichen', 'Haichou', 'Zhaohe', 'Yingrui', 'Yu Chang', 'Chien kang', 'Tung An']
seen = set()
for s in d.get('found', []):
    seen.add(s['name'])
    A('=' * 100)
    A('CShip %s   名字=%r   舰种=%r   +0x08=%s (hex %s)' % (s['ptr'], s['name'], s['t98'], s['tag08'], s['hex08']))
    A('  指向已知虚表对象的字段:')
    for r in s['refs']:
        if r['vt'] != '?(heap)': A('     +0x%-4x = %s   %s' % (r['off'], r['val'], r['vt']))
    A('  指向堆的字段 (前 12 个):')
    n = 0
    for r in s['refs']:
        if r['vt'] == '?(heap)':
            A('     +0x%-4x = %s' % (r['off'], r['val']))
            n += 1
            if n >= 12: break
A('')
A('--- 完整性检查 ---')
A('靶子名单: %s' % TARGET)
A('实际命中: %s' % sorted(seen))
missing = [t for t in TARGET if t not in seen]
A('缺少的: %s' % (missing if missing else '无 (9/9 全部命中)'))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('CShip 总数 = %s   命中靶子数 = %d' % (d.get('total'), len(d.get('found', []))))
for s in d.get('found', []):
    others = [r for r in s['refs'] if r['vt'] != '?(heap)']
    print('  %-20s %-12r %s' % (s['ptr'], s['name'], [(r['off'], r['vt']) for r in others]))
try: frida.kill(pid)
except Exception: pass
