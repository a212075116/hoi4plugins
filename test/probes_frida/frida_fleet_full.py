import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CGameState_CCountry_CFleet_完整枚举.txt'
JS = open(W + '/flirt/loader/_fleet_full.js', encoding='utf-8').read()
TAG = 'CHI'
args = [W + '/hoi4.exe', '-gdpr-compliant', '-start_tag=' + TAG, '-nolauncher']
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
print('[等待世界建立]', flush=True)
time.sleep(45)
n0 = sc.exports_sync.fleetCount()
print('[首次舰队计数] %s' % n0, flush=True)
time.sleep(20)
n1 = sc.exports_sync.fleetCount()
print('[稳定后舰队计数] %s' % n1, flush=True)
r = sc.exports_sync.run()
def dec(h):
    if h is None: return None
    try: return bytes.fromhex(h).decode('utf-8')
    except Exception: return '<非UTF8> ' + h
L = []
def a(s): L.append(str(s))
a('时间戳     : 20261009_015321')
a('测试模块   : 游戏根目录 hoi4.exe  (原版环境: 无 mod, dlc_load.json 的 enabled_mods 为空)')
a('启动参数   : %s' % ' '.join(args))
a('涉及类     : CGameState -> CCountry -> CFleet')
a('涉及函数   : CFleet::ctor sub_140D503D0 / 创建 sub_140D545A0 / 加入舰船 sub_140D51010')
a('             容器读取点 sub_1406D2EC0 / 名字来源 sub_140D55DC0 = qword_14332F0D8 (CUnitNamesDatabase)')
a('测试目的   : 全量解析 CFleet 的名字(+0xE0)与身份(tag + ref id)')
a('完整性     : 全量输出, 不抽样, 不过滤')
a('')
a('--- 判据链(全部来自反汇编) ---')
a('1. 容器  CCountry + 0x278 = CFleet* 数组, CCountry + 0x284 = 元素数')
a('   sub_1406D2EC0:')
a('     v6 = sub_140BB4390(&tag)      用 tag 取 CCountry*')
a('     v8 = *(DWORD*)(v6 + 644) - 1  CCountry + 0x284')
a('     sub_140D597F0(*(QWORD*)(*(QWORD*)(v6+632) + 8*v9), ship, 1)')
a('                                  CCountry + 0x278')
a('   sub_140BB4390 末尾: return *(QWORD*)(CGameState[98] + 8*v5)  98*8=784=0x310')
a('2. 名字  CFleet + 0xE0 CString, size 在 +0xF0, capacity 在 +0xF8')
a('   sub_140D503D0: malloc(0x20) -> +0xE0; +0xF0 = 18; +0xF8 = 31; strcpy(buf, "FLEET_NAME_NOT_SET")')
a('   sub_140D54430 / sub_140D545A0 里由 CUnitNamesDatabase 生成后写入 +0xE0')
a('3. 身份  CFleet + 0x08 = CReferenceObject { tag 低4字节, ref id 高4字节 }')
a('   断言佐证: pFleet->IsCreated() && "Added fleet has no ref id created!"')
a('             pFleet->GetCountry() == this && "Failed to set the country when adding a fleet!"')
a('4. 虚表 RVA 0x2962A18 (??_7CFleet@@6B@)  对象大小 0x130')
a('')
a('本次运行现场:')
a('hoi4.exe 基址 : %s' % r['base'])
a('CGameState*   : %s' % r['gs'])
a('省份数        : %s' % r['provinces'])
a('国家数        : %s' % r['countries'])
a('舰队元素总计数: %d' % r['totalFleets'])
a('结构化输出行数: %d' % len(r['rows']))
a('')
withF = [x for x in r['rows'] if x['fleets']]
a('有舰队槽位的国家数: %d / %d' % (len(withF), len(r['rows'])))
a('')
a('=' * 160)
a('%-6s %-20s %-20s %-6s %s' % ('国家', 'CCountry*', 'CFleet数组*', '舰队数', '舰队明细'))
a('=' * 160)
for x in r['rows']:
    det = []
    for f in x['fleets']:
        if f.get('null'): det.append('[%d NULL]' % f['fi']); continue
        if f.get('unreadable'): det.append('[%d 不可读 %s]' % (f['fi'], f.get('ptr'))); continue
        if f.get('err'): det.append('[%d 槽失败]' % f['fi']); continue
        det.append('[%d ptr=%s vt=%s tag=%s refid=%s name=%r |+0x48=%r |+0xB8=%r]' % (
            f['fi'], f.get('ptr'), ('吻合' if f.get('vtOk') else '不吻合'),
            f.get('tag'), f.get('refid'), dec(f.get('hex')), dec(f.get('hex48')), dec(f.get('hexB8'))))
    a('%-6d %-20s %-20s %-6s %s' % (x['ci'], x['c'], x.get('arr'), x.get('num'), ' '.join(det) if det else '(空)'))
a('')
a('--- 统计 ---')
ntot = 0; nvt = 0
names = {}; tags = {}
for x in r['rows']:
    for f in x['fleets']:
        if f.get('ptr'):
            ntot += 1
            if f.get('vtOk'): nvt += 1
            nm = dec(f.get('hex')); names[nm] = names.get(nm, 0) + 1
            t = f.get('tag'); tags[t] = tags.get(t, 0) + 1
a('CFleet 对象数   : %d' % ntot)
a('vtable 吻合     : %d' % nvt)
a('名字去重后      : %d' % len(names))
a('出现过的 tag 数 : %d' % len(tags))
a('')
a('名字清单(按出现次数降序):')
for k, v in sorted(names.items(), key=lambda kv: -kv[1]):
    a('    %-46r x%d' % (k, v))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s  行数=%d' % (OUT, len(L)))
print('')
print('省份数 %s / 国家数 %s' % (r['provinces'], r['countries']))
print('舰队元素总计数 : %d' % r['totalFleets'])
print('CFleet 对象数  : %d' % ntot)
print('vtable 吻合    : %d' % nvt)
print('名字去重后     : %d' % len(names))
for k, v in sorted(names.items(), key=lambda kv: -kv[1])[:15]:
    print('    %-46r x%d' % (k, v))
try: frida.kill(pid)
except Exception: pass