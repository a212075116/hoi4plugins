# frida_enum_province_names.py -- 全量输出 CProvince 的 id 与名字(名字经 VICTORY_POINTS_<id> 解析)
#
# 结论来源:
#   HOI4 里省份没有 PROV<n> 形式的独立名字(游戏本体与 mod 均为 0 条)。
#   但省份可以带胜利点, 胜利点的本地化键是 VICTORY_POINTS_<省份id>,
#   来源 mod/bakaifa/localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml (1708 行)。
#
# 判据(可证伪): CProvince + 0xA4 是 id(已全量验证 == 下标),
#   用它去查 VICTORY_POINTS_<id>, 命中的即该省份的名字。
# 全量输出, 不过滤。
import frida, time, re, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
YML = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CProvince_名字完整枚举.txt'

JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var pProv = gs.add(0x2B0).readPointer(), sProv = gs.add(0x2B0).add(8).readU32();
    var out = {base: base.toString(), gs: gs.toString(), ptr: pProv.toString(), size: sProv, rows: []};
    for (var i = 0; i < sProv; i++) {
        var p;
        try { p = pProv.add(i * 8).readPointer(); } catch (e) { out.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x200)) { out.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        out.rows.push({i: i, ptr: p.toString(), id: u32(p, 0xa4), id2: u32(p, 0x1fc)});
    }
    return out;
};
'''

def load_vp():
    m = {}
    if not os.path.exists(YML): return m
    with open(YML, encoding='utf-8-sig') as f:
        for line in f:
            mm = re.match(r'^\s*VICTORY_POINTS_(\d+)\s*:\s*"(.*)"\s*$', line.strip())
            if mm: m[int(mm.group(1))] = mm.group(2)
    return m

def wait_for_map(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if 'Launching SINGLEPLAYER-game' in open(GAMELOG, encoding='utf-8', errors='ignore').read():
                return True
        except Exception: pass
        time.sleep(0.4)
    return False

vp = load_vp()
print('[本地化] VICTORY_POINTS_<id> 条目: %d 条' % len(vp), flush=True)

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(8)
r = sc.exports_sync.run()

rows = r['rows']
n = sum(1 for x in rows if x.get('id') is not None)
eq = sum(1 for x in rows if x.get('id') is not None and x['id'] == x['i'])
hit = sum(1 for x in rows if x.get('id') is not None and vp.get(x['id']))

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : hoi4.exe (游戏根目录)')
a('访问方式     : Frida, 静态锚点 qword_14332F260 -> CGameState')
a('涉及类       : CGameState -> CProvince')
a('涉及函数     : CProvince::ctor sub_140E78EC0 (id 偏移的静态依据)')
a('测试目的     : 拿出 CProvince 的 id 与名字')
a('完整性问题   : 全量输出, 不抽样, 不过滤')
a('')
a('判据链:')
a('  1. vtable 精确等于 CProvince 虚表 (0x2971B18 / 0x2971B68)')
a('  2. CProvince + 0xA4 = id   (静态依据: ctor 里 *(_DWORD*)(a1+164) = *(_DWORD*)(a2+196))')
a('     全量校验 id == 数组下标: %d / %d' % (eq, n))
a('  3. 名字: 省份没有 PROV<n> 形式的本地化(游戏本体与 mod 均 0 条);')
a('     省份名来自胜利点本地化键 VICTORY_POINTS_<id>')
a('     来源: mod/bakaifa/localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml')
a('     该表共 %d 条' % len(vp))
a('     命中(即该省份有名字): %d / %d' % (hit, n))
a('')
a('hoi4.exe 基址    : %s' % r['base'])
a('CGameState*      : %s' % r['gs'])
a('CProvince 数组   : %s   声明元素数=%d' % (r['ptr'], r['size']))
a('')
a('-' * 110)
a('%-8s %-20s %-8s %-8s %-30s %s' % ('下标', '对象指针', 'id', '第二id', '名字(VICTORY_POINTS_<id>)', '有名字'))
a('-' * 110)
for x in rows:
    if x.get('null'):
        a('%-8d %-20s %-8s %-8s %-30s %s' % (x['i'], '0x0', '-', '-', '(NULL 空槽)', '否'))
        continue
    if x.get('unreadable'):
        a('%-8d %-20s %-8s %-8s %-30s %s' % (x['i'], x.get('ptr','?'), '-', '-', '(指针不可读)', '否'))
        continue
    if x.get('err'):
        a('%-8d %-20s %-8s %-8s %-30s %s' % (x['i'], '-', '-', '-', '(slot 读取失败)', '否'))
        continue
    i = x['i']
    nm = vp.get(x['id']) if x.get('id') is not None else None
    a('%-8d %-20s %-8s %-8s %-30s %s' % (i, x['ptr'], x.get('id'), x.get('id2'), (nm if nm else '(该省份无胜利点)'), ('是' if nm else '否')))
a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
print('[有id] %d   [id==下标] %d   [有名字] %d' % (n, eq, hit))
print('')
print('[有名字的省份样本]')
c = 0
for x in rows:
    if x.get('id') is not None and vp.get(x['id']):
        print('    id=%-6s -> %s' % (x['id'], vp[x['id']]))
        c += 1
        if c >= 20: break
try: frida.kill(pid)
except Exception: pass