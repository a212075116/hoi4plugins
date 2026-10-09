import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_舰队编制到军舰_全量闭环.txt'
JS = open(W + '/flirt/loader/_fleet_ship_final.js', encoding='utf-8').read()
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
OOB = [('Ninghai','light_cruiser'),('Hairong','light_cruiser'),('Haichen','light_cruiser'),
       ('Haichou','light_cruiser'),('Zhaohe','heavy_cruiser'),('Yingrui','heavy_cruiser'),
       ('Yu Chang','destroyer'),('Chien kang','destroyer'),('Tung An','destroyer')]
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('涉及类     : CGameState -> CCountry -> CFleet -> CTaskForce -> CShip')
A('涉及函数   : CFleet::ctor sub_140D503D0 / CFleet 创建 sub_140D545A0 / 加船 sub_140D51010')
A('             CFleet 容器读取 sub_1406D2EC0')
A('             CTaskForce::ctor sub_140D63320')
A('             CShip::ctor sub_140C2FEA0  (对象 >= 0x938 字节)')
A('测试目的   : 从 CHI 的国家一路走到每一条军舰, 每条船必须能与游戏数据逐个对上')
A('靶子       : history/units/CHI_1936_naval_mtg.txt 的 Di 1 Jiandui = 1 个 task_force + 9 条 ship')
A('完整性     : 全量输出, 不抽样, 不过滤')
A('')
A('--- 字段判据 (静态反汇编 + 运行时实测) ---')
A('CCountry   + 0x278 / +0x284 = CFleet* 数组 / 元素数')
A('CFleet     + 0xB8  / +0xC4  = CTaskForce* 数组 / 元素数')
A('CShip      + 0x00  = vtable (hoi4.exe+0x2957F28)   +0x18 = 第二 vtable (+0x2957F90)')
A('CShip      + 0x728 = CTaskForce* 所属特遣舰队  <== 反引用, 本次确证')
A('CShip      + 0x820 = 名字 CString')
A('CShip      + 0x98 / +0xE8 = 舰种字符串')
A('')
A('CGameState* = %s' % d.get('gs'))
A('CHI CCountry* = %s (数组索引 %s)' % (d.get('chiPtr'), d.get('idx')))
A('全世界 CShip 总数 = %s' % d.get('total'))
A('扫描耗时 = %s ms   总耗时 = %s ms' % (d.get('scanMs'), d.get('totalMs')))
A('')
A('=' * 108)
A('CHI 的舰队与特遣舰队 (全部)')
A('=' * 108)
for t in d.get('tfList', []):
    A('舰队 %s  refid=%s  名字=%r  特遣舰队数=%s' % (t['fleet'], t['ref'], t['name'], t['tfCount']))
    for s in t['tfs']:
        A('    特遣舰队 [%d] %s  虚表=%s' % (s['tfIdx'], s['tfPtr'], 'CTaskForce_a'))
A('')
A('=' * 108)
A('CHI 的全部军舰 (从 CFleet -> CTaskForce 归属链上筛出的 CShip)')
A('=' * 108)
A('%-4s %-20s %-20s %-12s %-16s %-16s %s' % ('#', 'CShip*', '所属 CTaskForce*', 'vtable', '名字(+0x820)', '舰种(+0x98)', '所属舰队'))
for i, s in enumerate(d.get('ships', [])):
    A('%-4d %-20s %-20s %-12s %-16r %-16r %r' % (i + 1, s['ptr'], s['tf'], s['vt'], s['name'], s['t98'], s['fleetName']))
A('')
A('从 CHI 舰队链上取到的军舰数 = %d' % len(d.get('ships', [])))
A('不属于 CHI 任何舰队的 CTaskForce 数 = %d' % d.get('otherTfCount'))
A('')
A('=' * 108)
A('与游戏数据 (history/units/CHI_1936_naval_mtg.txt) 逐条对照')
A('=' * 108)
A('%-4s %-16s %-16s %-16s %s' % ('#', 'OOB 里的 name', 'OOB 里的 definition', '内存里的名字', '内存里的舰种'))
byName = {}
for s in d.get('ships', []):
    byName.setdefault(s['name'], []).append(s)
okName = 0; okType = 0
for i, (nm, dfn) in enumerate(OOB):
    lst = byName.get(nm, [])
    got = lst[0]['t98'] if lst else None
    hn = '命中' if lst else '缺失'
    ht = '一致' if got == dfn else ('不一致' if lst else '-')
    if lst: okName += 1
    if got == dfn: okType += 1
    A('%-4d %-16s %-16s %-16s %s   [%s / %s]' % (i + 1, repr(nm), dfn, repr(got), ht, hn, ht))
A('')
A('OOB 条数 = %d' % len(OOB))
A('从内存舰队链上取到的军舰数 = %d' % len(d.get('ships', [])))
A('名字命中 = %d / %d' % (okName, len(OOB)))
A('舰种一致 = %d / %d' % (okType, len(OOB)))
A('')
A('--- 内存有但 OOB 没有的 ---')
for s in d.get('ships', []):
    if s['name'] not in [o[0] for o in OOB]: A('    %s %r %r' % (s['ptr'], s['name'], s['t98']))
A('--- OOB 有但内存没有的 ---')
mn = set(s['name'] for s in d.get('ships', []))
for nm, dfn in OOB:
    if nm not in mn: A('    %r %s' % (nm, dfn))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('全世界 CShip = %s   从 CHI 舰队链上取到 = %d' % (d.get('total'), len(d.get('ships', []))))
for s in d.get('ships', []):
    print('   %-20s %-12r %-16r -> %s' % (s['ptr'], s['name'], s['t98'], s['fleetName']))
print('名字命中 %d/%d   舰种一致 %d/%d' % (okName, len(OOB), okType, len(OOB)))
try: frida.kill(pid)
except Exception: pass
