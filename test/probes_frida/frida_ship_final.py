import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_CFleet_CTaskForce_CShip_完整枚举.txt'
JS = open(W + '/flirt/loader/_ship_final.js', encoding='utf-8').read()
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
d = sc.exports_sync.run()
OOB = [('Ninghai','light_cruiser','Ninghai Class'),('Hairong','light_cruiser','Hai Yung Class'),
       ('Haichen','light_cruiser','Hai Yung Class'),('Haichou','light_cruiser','Hai Yung Class'),
       ('Zhaohe','heavy_cruiser','Chao Ho Class'),('Yingrui','heavy_cruiser','Chao Ho Class'),
       ('Yu Chang','destroyer','Chiang Feng Class'),('Chien kang','destroyer','Chiang Feng Class'),
       ('Tung An','destroyer','Chiang Feng Class')]
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('涉及类     : CGameState -> CCountry -> CFleet -> CTaskForce -> CShip')
A('涉及函数   : CFleet::ctor sub_140D503D0 / 创建 sub_140D545A0 / 加船 sub_140D51010')
A('             CFleet 容器读取 sub_1406D2EC0')
A('             CTaskForce::ctor sub_140D63320 (虚表写入 +0/+0x10/+0xB8/+0x338)')
A('             CTaskForce 遍历船数组 sub_140D63620: for(i=*(a1+1832); i!=&i[*(int*)(a1+1844)]; ++i)')
A('             CShip::ctor sub_140C2FEA0')
A('测试目的   : 把 CHI 的 CFleet 下的 CTaskForce 下的每个军舰(CShip)逐个取出来')
A('靶子       : history/units/CHI_1936_naval_mtg.txt 的 Di 1 Jiandui = 1 个 task_force + 9 条 ship')
A('完整性     : 全量输出, 不抽样, 不过滤')
A('')
A('--- 字段判据 ---')
A('CCountry + 0x278 / +0x284 = CFleet* 数组 / 元素数')
A('CFleet   + 0xB8  / +0xC4  = CTaskForce* 数组 / 元素数')
A('CTaskForce + 0x728 / +0x734 = CShip* 数组 / 元素数   <== 本次新确证')
A('CShip    + 0x00 = vtable (hoi4.exe+0x2957F28)')
A('CShip    + 0x820 = 名字 CString')
A('CShip    + 0x98  = 舰种字符串 (destroyer/light_cruiser/heavy_cruiser/...)')
A('CShip    + 0xE8  = 舰种字符串 (同上)')
A('')
A('CGameState* = %s   CHI CCountry* = %s (索引 %s)' % (d.get('gs'), d.get('chiPtr'), d.get('idx')))
A('CHI 舰队数 = %s' % d.get('fleetCount'))
A('')
real = []
for f in d.get('fleets', []):
    A('=' * 100)
    A('[舰队 %d] %s   名字=%r' % (f['i'], f['ptr'], f['name']))
    A('   CFleet+0xB8 = %s   CFleet+0xC4 = %s' % (f['tfData'], f['tfCount']))
    for tf in f['tfs']:
        A('   [特遣舰队 %d] %s  vtable=%s' % (tf['i'], tf['ptr'], tf['vt']))
        A('      CTaskForce+0x728 = %s   CTaskForce+0x734 = %s' % (tf['shipsData'], tf['shipCount']))
        A('      --- 军舰全量 (%s 条) ---' % tf['shipCount'])
        A('      %-4s %-20s %-12s %-32s %-16s %-16s' % ('#', 'CShip*', 'vtable', '名字(+0x820)', '舰种(+0x98)', '舰种(+0xE8)'))
        for s in tf['ships']:
            A('      %-4d %-20s %-12s %-32r %-16r %-16r' % (s['i'], s['ptr'], s['vt'], s['name'], s['t98'], s['tE8']))
            real.append(s)
        A('')
A('=' * 100)
A('--- 与游戏数据 (CHI_1936_naval_mtg.txt) 逐条对照 ---')
A('%-4s %-32s %-16s %-16s' % ('#', 'OOB 里的名字', 'OOB 里的 definition', '内存里读到的舰种'))
mem = {s['name']: s for s in real}
ok = 0
for i, (nm, dfn, vn) in enumerate(OOB):
    m = mem.get(nm)
    got = m['t98'] if m else None
    hit = (got == dfn)
    if hit: ok += 1
    A('%-4d %-32s %-16s %-16s  %s' % (i + 1, repr(nm), dfn, repr(got), '一致' if hit else '不一致'))
A('')
A('OOB 条数 = %d   内存里 CHI 舰队的 CShip 数 = %d   名字+舰种都一致 = %d' % (len(OOB), len(real), ok))
A('')
A('--- 内存里有但 OOB 对照表里没有的 ---')
for s in real:
    if s['name'] not in [o[0] for o in OOB]: A('    %s %r %r' % (s['ptr'], s['name'], s['t98']))
A('--- OOB 有但内存里没有的 ---')
mn = set(s['name'] for s in real)
for nm, dfn, vn in OOB:
    if nm not in mn: A('    %r %s' % (nm, dfn))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for f in d.get('fleets', []):
    for tf in f['tfs']:
        print('特遣舰队 %s 船数=%s' % (tf['ptr'], tf['shipCount']))
        for s in tf['ships']:
            print('   %-4d %-20s %-12s %-24r %r' % (s['i'], s['ptr'], s['vt'], s['name'], s['t98']))
print('')
print('OOB=%d  内存=%d  一致=%d' % (len(OOB), len(real), ok))
try: frida.kill(pid)
except Exception: pass
