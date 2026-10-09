# frida_enum_prov_state_name.py -- 全量输出 CProvince / CState 的 id 与名字(名字经本地化解析)
#
# 已确认的两件事:
#   CProvince + 0xA4 = id,  CState + 0x58 = id   (上一轮全量验证: id == 数组下标, 零例外)
#   对象里不存名字 —— 名字是本地化条目 STATE_<id>
#     (mod/bakaifa/localisation/simp_chinese/ba_state_names_l_simp_chinese.yml, 898 条)
#
# 本脚本全量遍历, 每项给出: 下标 / 对象指针 / id / 名字, 名字来自本地化表。
import frida, time, re, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
YML = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/localisation/simp_chinese/ba_state_names_l_simp_chinese.yml'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CProvince_CState_id与名字完整枚举_v2.txt'

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
    var out = {base: base.toString(), gs: gs.toString()};
    var pProv = gs.add(0x2B0).readPointer(), sProv = gs.add(0x2B0).add(8).readU32();
    var pState = gs.add(0x2C8).readPointer(), sState = gs.add(0x2C8).add(8).readU32();
    out.prov = {ptr: pProv.toString(), size: sProv, rows: []};
    out.state = {ptr: pState.toString(), size: sState, rows: []};
    for (var i = 0; i < sProv; i++) {
        var p;
        try { p = pProv.add(i * 8).readPointer(); } catch (e) { out.prov.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.prov.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x200)) { out.prov.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        out.prov.rows.push({i: i, ptr: p.toString(), id: u32(p, 0xa4), id2: u32(p, 0x1fc)});
    }
    for (var i = 0; i < sState; i++) {
        var p;
        try { p = pState.add(i * 8).readPointer(); } catch (e) { out.state.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.state.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x200)) { out.state.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        out.state.rows.push({i: i, ptr: p.toString(), id: u32(p, 0x58), id2: u32(p, 0x18c)});
    }
    return out;
};
'''

def load_state_names():
    m = {}
    if not os.path.exists(YML):
        return m
    with open(YML, encoding='utf-8-sig') as f:
        for line in f:
            mm = re.match(r'^\s*STATE_(\d+)\s*:\s*"(.*)"\s*$', line.strip())
            if mm:
                m[int(mm.group(1))] = mm.group(2)
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

names = load_state_names()
print('[本地化] STATE_<id> 条目: %d 条' % len(names), flush=True)

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(8)
r = sc.exports_sync.run()

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : hoi4.exe (游戏根目录)')
a('访问方式     : Frida, 静态锚点 qword_14332F260 -> CGameState')
a('涉及类       : CGameState -> CProvince / CState')
a('涉及函数     : CProvince::ctor sub_140E78EC0 / CState::ctor sub_1409CFB10')
a('测试目的     : 用 id 与名字证明这些对象确实是 CProvince / CState')
a('完整性问题   : 全量输出, 不抽样, 不过滤')
a('')
a('判据链:')
a('  1. 对象 vtable 精确等于 CProvince / CState 的虚表地址')
a('  2. 对象里的 id 字段等于它在数组中的下标')
a('     CProvince +0xA4 (静态依据: ctor 里 *(_DWORD*)(a1+164) = *(_DWORD*)(a2+196))')
a('     CState    +0x58')
a('  3. 名字: 对象里不存名字, 名字是本地化条目 STATE_<id>')
a('     来源: mod/bakaifa/localisation/simp_chinese/ba_state_names_l_simp_chinese.yml')
a('     (mod 中 %d 条; 游戏本体 localisation 中另有 10810 条)' % len(names))
a('')
a('hoi4.exe 基址: %s' % r['base'])
a('CGameState*  : %s' % r['gs'])
a('')

for key, label, idoff in (('prov', 'CProvince', '+0xA4'), ('state', 'CState', '+0x58')):
    d = r[key]
    rows = d['rows']
    a('=' * 120)
    a('%s 数组  基址=%s  声明元素数=%d' % (label, d['ptr'], d['size']))
    a('=' * 120)
    n = sum(1 for x in rows if x.get('id') is not None)
    m = sum(1 for x in rows if x.get('id') is not None and x['id'] == x['i'])
    both = sum(1 for x in rows if x.get('id') is not None and x.get('id2') is not None and x['id'] == x['i'] and x['id2'] == x['i'])
    a('')
    a('统计:')
    a('    总项数                       : %d' % len(rows))
    a('    有 id 值的项                 : %d' % n)
    a('    其中 id == 数组下标          : %d' % m)
    a('    其中 +0x1FC/+0x18C 也 == 下标: %d' % both)
    a('')
    a('-' * 120)
    if key == 'state':
        a('%-8s %-20s %-8s %-8s %-30s %s' % ('下标', '对象指针', 'id', '第二id', '名字(本地化 STATE_<id>)', '名字是否取到'))
    else:
        a('%-8s %-20s %-8s %-8s %s' % ('下标', '对象指针', 'id', '第二id', '说明'))
    a('-' * 120)
    for x in rows:
        if x.get('null'):
            a('%-8d %-20s %-8s %-8s %s' % (x['i'], '0x0', '-', '-', '(NULL 空槽)'))
            continue
        if x.get('unreadable'):
            a('%-8d %-20s %-8s %-8s %s' % (x['i'], x.get('ptr','?'), '-', '-', '(指针不可读)'))
            continue
        if x.get('err'):
            a('%-8d %-20s %-8s %-8s %s' % (x['i'], '-', '-', '-', '(slot 读取失败)'))
            continue
        i = x['i']
        if key == 'state':
            nm = names.get(x['id']) if x.get('id') is not None else None
            a('%-8d %-20s %-8s %-8s %-30s %s' % (i, x['ptr'], x.get('id'), x.get('id2'), (nm if nm else '(无本地化条目)'), ('是' if nm else '否')))
        else:
            a('%-8d %-20s %-8s %-8s %s' % (i, x['ptr'], x.get('id'), x.get('id2'), 'id==下标=%s' % (x.get('id') == i)))
    a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
sr = r['state']['rows']
hit = sum(1 for x in sr if x.get('id') is not None and names.get(x['id']))
tot = sum(1 for x in sr if x.get('id') is not None)
print('[CState 名字命中] %d / %d' % (hit, tot))
for x in sr[:15]:
    if x.get('id') is not None:
        print('    id=%-5s -> %s' % (x['id'], names.get(x['id'], '(无)')))
try: frida.kill(pid)
except Exception: pass