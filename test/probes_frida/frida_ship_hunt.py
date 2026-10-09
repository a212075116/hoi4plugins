import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CShip_名字与归属全量.txt'
JS = open(W + '/flirt/loader/_ship_hunt.js', encoding='utf-8').read()
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
print('[扫描 CShip + 名字 + 归属]', flush=True)
r = sc.exports_sync.scanStrings()
with open(W + '/reports/_ship_raw.json', 'w', encoding='utf-8') as fp: json.dump(r, fp, ensure_ascii=False)
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 全量列出所有 CShip 的名称与是否属于 CHI')
A('靶子       : CHI_1936_naval_mtg.txt 的 Di 1 Jiandui = 9 条船')
A('完整性     : 全量 %d 个 CShip, 不抽样, 不过滤' % r.get('total'))
A('')
A('CHI CCountry* = %s' % r.get('chiPtr'))
A('CShip 总数 = %s   耗时 = %s ms' % (r.get('total'), r.get('ms')))
A('')
chi = [s for s in r['ships'] if s['chi']]
A('属于 CHI 的 CShip 数 = %d' % len(chi))
A('')
A('--- 属于 CHI 的 CShip 全量 ---')
for s in chi:
    A('  %s   chiOff=%s' % (s['ptr'], s['chiOff']))
    for n in s['names']:
        A('      +0x%-4x %r' % (n['off'], n['name']))
A('')
A('--- 全部 %d 个 CShip 的名字字段 (仅列有名字的) ---' % r['total'])
for s in r['ships']:
    if not s['names'] and not s['chi']: continue
    A('  %s  chi=%s' % (s['ptr'], s['chi']))
    for n in s['names']:
        A('      +0x%-4x %r' % (n['off'], n['name']))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('属于 CHI 的 CShip 数 = %d' % len(chi))
for s in chi:
    print('   %s chiOff=%s 名字=%s' % (s['ptr'], s['chiOff'], [n['name'] for n in s['names']]))
try: frida.kill(pid)
except Exception: pass
