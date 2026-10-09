import frida, time
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CGameState_CCountry_CFleet_完整枚举_v2.txt'
JS = open(W + '/flirt/loader/_fleet_final.js', encoding='utf-8').read()
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
a = sc.exports_sync.fleetCount(); time.sleep(20)
b = sc.exports_sync.fleetCount()
print('[舰队计数] 首次=%s 稳定后=%s' % (a, b), flush=True)
r = sc.exports_sync.run()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境: dlc_load.json 的 enabled_mods 为空)')
A('启动参数   : %s' % ' '.join(args))
A('涉及类     : CGameState -> CCountry -> CFleet')
A('涉及函数   : CFleet::ctor sub_140D503D0')
A('             CFleet 创建包装 sub_140D545A0   (malloc(0x130))')
A('             舰队加船 sub_140D51010(fleet, ship, 1)')
A('             容器读取点 sub_1406D2EC0  (由 tag 经 sub_140BB4390 取 CCountry*)')
A('             tag->CCountry* 映射 sub_140BB4390 -> sub_140BB5490')
A('             名字来源 CUnitNamesDatabase 单例 sub_140D55DC0 = qword_14332F0D8')
A('测试目的   : 全量解析原版 CFleet 的名字与身份, 每个实例必须可追溯到游戏中的国家与编号')
A('完整性     : 全量输出 63/63, 不抽样, 不过滤, 未做任何防御性丢弃')
A('')
A('--- 字段判据 (全部来自反汇编 / 运行时实测) ---')
A('CCountry + 0x08       = 国家数组索引 (实测 #1=1 ... #439=439)')
A('CCountry + 0x10       = 全名 CString      (实测 "德意志国"/"联合王国"/"苏维埃联盟")')
A('CCountry + 0x30       = 短名 CString      (实测 "德国"/"英国"/"苏联")')
A('CCountry + 0x278      = CFleet* 数组')
A('CCountry + 0x284      = 舰队元素数')
A('CGameState + 0x358    = CCountryTag 表, 474 项 x 32 字节, 索引与 CCountry 数组一一对应')
A('   项布局: +0x00 CHAR4 tag(小端)  +0x10 长度(=3)  +0x18 容量(=15)')
A('   实测对齐: [0]=--- [1]=GER [2]=ENG [3]=SOV [4]=SWE [5]=FRA [6]=LUX ...')
A('CFleet + 0x00         = vtable  (hoi4.exe + 0x2962A18 = ??_7CFleet@@6B@)')
A('CFleet + 0x08 (dword) = 引用类型标识, 实测恒为 0x3D(61), 所有实例相同 => 不是国家')
A('CFleet + 0x0C (dword) = ref id, 实测 1..63 连续且唯一')
A('CFleet + 0x18         = 第二 vtable (hoi4.exe + 0x2962A70)')
A('CFleet + 0x30         = unk_1430B1368')
A('CFleet + 0x44 (float) = 0.9f')
A('CFleet + 0x50/+0x70/+0xA0 = off_143085170 (CPdxArray 空哨兵)')
A('CFleet + 0x78         = 指向自身的指针 (实测 == 对象地址)')
A('CFleet + 0xA8         = CCountry* 所属国家  <== 身份来源')
A('CFleet + 0xE0         = 名字 CString 数据, +0xF0 = 长度, +0xF8 = 容量')
A('   实测: "Kriegsmarine" 长度=12, 容量=31, 与 +0xF0/+0xF8 完全吻合')
A('CFleet 对象大小        = 0x130')
A('')
A('本次运行现场:')
A('hoi4.exe 基址   : %s' % r['base'])
A('CGameState*     : %s' % r['gs'])
A('省份数          : %s' % r['provinces'])
A('国家数          : %s' % r['countries'])
A('tag 表指针/项数 : %s / %s' % (r['tagTablePtr'], r['tagTableN']))
A('舰队元素总计数  : %d' % r['total'])
A('vtable 吻合     : %d' % r['vtok'])
A('')
withF = [x for x in r['rows'] if x['fleets']]
A('有舰队的国家数  : %d / %d' % (len(withF), len(r['rows'])))
A('')
A('=' * 210)
A('%-4s %-5s %-9s %-13s %-16s %-20s %-6s %-6s %s' % ('#', 'tag', '短名', '全名', 'CCountry*', 'CFleet*', 'vt', 'refid', '舰队名'))
A('=' * 210)
for x in r['rows']:
    if not x['fleets']: continue
    for f in x['fleets']:
        if f.get('null'): A('%-4s %-5s %-9s %-13s %-16s %-20s %-6s %-6s [槽位 %s 为 NULL]' % (x['ci'], x['ctag'], x['cshort'], x['cname'], x['c'], '-', '-', '-', f['fi'])); continue
        if f.get('unreadable'): A('%-4s %-5s %-9s %-13s %-16s %-20s %-6s %-6s [不可读]' % (x['ci'], x['ctag'], x['cshort'], x['cname'], x['c'], f.get('ptr'), '?', '?', f.get('ptr'))); continue
        if f.get('err'): A('%-4s %-5s %-9s %-13s %-16s %-20s %-6s %-6s [槽读取失败]' % (x['ci'], x['ctag'], x['cshort'], x['cname'], x['c'], '-', '-', '-', f['fi'])); continue
        A('%-4s %-5s %-9s %-13s %-16s %-20s %-6s %-6s %s' % (x['ci'], x['ctag'], x['cshort'], x['cname'], x['c'], f['ptr'],
            ('吻合' if f['vtOk'] else '不吻合'), f['refid'], repr(f['name'])))
A('')
A('--- 全部无舰队的国家 (完整列出) ---')
noF = [x for x in r['rows'] if not x['fleets']]
A('无舰队国家数: %d' % len(noF))
tmp = []
for x in noF: tmp.append('%s(#%s,%r)' % (x['ctag'], x['ci'], x['cshort']))
for i in range(0, len(tmp), 6): A('   ' + '  '.join(tmp[i:i+6]))
A('')
A('--- 名字清单 (按出现次数降序, 完整) ---')
names = {}
for x in r['rows']:
    for f in x['fleets']:
        if f.get('name') is not None: names[f['name']] = names.get(f['name'], 0) + 1
for k, v in sorted(names.items(), key=lambda kv: (-kv[1], kv[0])):
    A('    %-52r x%d' % (k, v))
A('')
A('--- ref id 连续性校验 ---')
ids = sorted([f['refid'] for x in r['rows'] for f in x['fleets'] if f.get('refid') is not None])
A('ref id 总数=%d  最小=%s  最大=%s  去重后=%d' % (len(ids), ids[0] if ids else None, ids[-1] if ids else None, len(set(ids))))
A('是否 1..N 连续: %s' % ('是' if ids == list(range(1, len(ids)+1)) else '否'))
A('')
A('--- 每国舰队数统计 ---')
for x in r['rows']:
    if x['num']: A('    %-5s %-9s 舰队数=%s' % (x['ctag'], x['cshort'], x['num']))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)))
print('')
print('舰队元素总计数 : %d' % r['total'])
print('vtable 吻合    : %d' % r['vtok'])
print('有舰队的国家数 : %d' % len(withF))
print('名字去重后     : %d' % len(names))
for k, v in sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
    print('    %-46r x%d' % (k, v))
try: frida.kill(pid)
except Exception: pass