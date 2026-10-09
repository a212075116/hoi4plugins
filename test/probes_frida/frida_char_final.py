# frida_char_final.py -- 全量输出 CCharacter 的 id 与名字
#
# 静态依据(全部来自反汇编, 不是猜测):
#   [管理器] CGameState + 0x6A8
#     sub_1410DCDF0: v24 = *((_QWORD *)Invalid_country_tag + 213);   213*8 = 0x6A8
#     Invalid_country_tag 即 CGameState::_pInstance
#     断言证实 "_pInstance && \"gamestate unitilialized\"" @ gamestate.h:1116
#   [管理器结构] sub_1406B70B0(mgr, src)
#     +0x08 计数器   +0x10 数组数据指针   +0x1C 元素数
#     sub_1406B2A10(mgr+16, &obj) 追加;  sub_1406B4CA0 取元素
#   [名字] CCharacter + 0x48, CString(Capacity/Size 在 +0x58/+0x60)
#     构造函数 sub_140F9EC50(this, name, id) 里 sub_14011E010(a1 + 72, a2)
#   [大小] 0x130  (sub_1406B70B0 / sub_140FA0A20 里的 malloc(0x130))
#   [虚表] CCharacter @ RVA 0x297EA60
#
# id 字段是动态测出来的: 对 2451 个对象的每个 4 字节偏移统计唯一值个数,
# 只有 +0xC 给出 2451 个唯一值且范围 1..2455(连续), 其余完全唯一的偏移都是指针。
# 报告见 reports/char_fields_unique.txt
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CCharacter_id与名字完整枚举_v2.txt'

JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_CHAR = base.add(0x297EA60);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
// 返回名字的原始字节的 hex, 交给 Python 按 UTF-8 解码
function readCSHex(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz > 300 || cap < sz || cap > 300) return null;
        if (sz === 0) return '';
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) {
            var h = dp.add(i).readU8().toString(16);
            if (h.length === 1) h = '0' + h;
            s += h;
        }
        return s;
    } catch (e) { return null; }
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.ready = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull()) return {ok: false, why: 'GS=NULL'};
        if (!readable(gs, 0x800)) return {ok: false, why: 'GS 不可读'};
        var sProv = gs.add(0x2B0).add(8).readU32();
        if (sProv < 9000) return {ok: false, why: 'prov=' + sProv};
        var mgr = gs.add(0x6A8).readPointer();
        if (mgr.isNull()) return {ok: false, why: 'mgr=NULL'};
        if (!readable(mgr, 0x40)) return {ok: false, why: 'mgr 不可读'};
        var sz = u32(mgr, 0x1c);
        if (!sz) return {ok: false, why: 'mgrsize=0'};
        return {ok: true, gs: gs.toString(), mgr: mgr.toString(), prov: sProv, mgrSize: sz};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var mgr = gs.add(0x6A8).readPointer();
    var arr = mgr.add(0x10).readPointer();
    var size = u32(mgr, 0x1c);
    var out = {base: base.toString(), gs: gs.toString(), mgr: mgr.toString(),
               counter: u32(mgr, 8), arrPtr: arr.toString(), size: size, rows: []};
    for (var i = 0; i < size; i++) {
        var p;
        try { p = arr.add(i * 8).readPointer(); } catch (e) { out.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x130)) { out.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        var vt = null; try { vt = p.readPointer(); } catch (e) {}
        out.rows.push({i: i, ptr: p.toString(), vtOk: (vt && vt.equals(VT_CHAR)),
                       id: u32(p, 0x0c), f18: u32(p, 0x18), hex: readCSHex(p.add(0x48))});
    }
    return out;
};
'''

def wait_for_map(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if 'Launching SINGLEPLAYER-game' in open(GAMELOG, encoding='utf-8', errors='ignore').read():
                return True
        except Exception: pass
        time.sleep(0.4)
    return False

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
t0 = time.time(); last = None
while time.time() - t0 < 420:
    try: st = sc.exports_sync.ready()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'): print('[就绪] %s' % st, flush=True); break
    if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    frida.kill(pid); raise SystemExit('超时')

r = sc.exports_sync.run()
rows = r.get('rows') or []

names = []
for x in rows:
    h = x.get('hex')
    if h is None: names.append(None); continue
    try: names.append(bytes.fromhex(h).decode('utf-8'))
    except Exception: names.append('<非UTF8>: ' + h)

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : 游戏根目录 hoi4.exe')
a('涉及类       : CGameState -> (管理器 @ +0x6A8) -> CCharacter')
a('涉及函数     : CCharacter::ctor            sub_140F9EC50')
a('               CCharacter 创建            sub_1406B70B0 / sub_1406B7510')
a('               上层创建点                sub_1410DCDF0 / sub_140357BE0')
a('               数组追加 / 取元素          sub_1406B2A10 / sub_1406B4CA0')
a('测试目的     : 拿出 CCharacter 的 id 与名字')
a('完整性       : 全量输出, 不抽样, 不过滤; 每一行都对应数组里的一个真实槽位')
a('')
a('--- 判据链 ---')
a('1. 管理器位置  CGameState + 0x6A8')
a('   sub_1410DCDF0 反编译: v24 = *((_QWORD *)Invalid_country_tag + 213);  213*8 = 0x6A8')
a('   Invalid_country_tag 即 CGameState::_pInstance (断言 gamestate.h:1116 证实)')
a('2. 管理器结构  sub_1406B70B0(mgr, src):')
a('   +0x08 计数器   +0x10 数组数据指针   +0x1C 元素数')
a('3. id 字段  CCharacter + 0x0C  —— 动态测出, 不是推断:')
a('   对 2451 个对象的每个 4 字节偏移统计唯一值个数, 结果:')
a('     +0x0C  唯一值 2451  范围 1..2455   <= 唯一且连续, 即 id')
a('     +0x80  唯一值 2451  范围 指针      (指针字段)')
a('     +0x98  唯一值 2451  范围 指针')
a('     +0xB0  唯一值 2451  范围 指针')
a('     +0xD0  唯一值 2451  范围 指针')
a('   其余偏移的唯一值数全部小于 2451。完整表见 reports/char_fields_unique.txt')
a('4. 名字字段  CCharacter + 0x48')
a('   构造函数 sub_140F9EC50(this, name, id) 里 sub_14011E010(a1 + 72, a2)')
a('5. 对象大小 0x130;  虚表 RVA 0x297EA60')
a('')
a('--- 本次运行现场 ---')
a('hoi4.exe 基址   : %s' % r['base'])
a('CGameState*     : %s' % r['gs'])
a('管理器 +0x6A8   : %s' % r['mgr'])
a('计数器 +0x08    : %s' % r.get('counter'))
a('数组   +0x10    : %s' % r.get('arrPtr'))
a('元素数 +0x1C    : %s' % r.get('size'))
a('')
ids = [x['id'] for x in rows if x.get('id') is not None]
valid = [n for n in names if n is not None]
vt = sum(1 for x in rows if x.get('vtOk'))
uniqIds = len(set(ids)); uniqNames = len(set(valid))
a('--- 统计 ---')
a('总槽位              : %d' % len(rows))
a('有 id 的槽位        : %d' % len(ids))
a('读得出名字的槽位    : %d' % len(valid))
a('vtable 吻合的槽位   : %d' % vt)
a('id 去重后           : %d' % uniqIds)
a('名字去重后          : %d' % uniqNames)
if ids: a('id 范围             : %d .. %d' % (min(ids), max(ids)))
a('')
a('=' * 112)
a('%-8s %-20s %-8s %-10s %-8s %s' % ('下标', '对象指针', 'id', '+0x18', 'vtable', '名字'))
a('=' * 112)
for k, x in enumerate(rows):
    if x.get('null'):
        a('%-8d %-20s %-8s %-10s %-8s %s' % (x['i'], '0x0', '-', '-', '-', '(NULL 空槽)')); continue
    if x.get('unreadable'):
        a('%-8d %-20s %-8s %-10s %-8s %s' % (x['i'], x.get('ptr'), '-', '-', '-', '(指针不可读)')); continue
    if x.get('err'):
        a('%-8d %-20s %-8s %-10s %-8s %s' % (x['i'], '-', '-', '-', '-', '(槽位读取失败)')); continue
    a('%-8d %-20s %-8s %-10s %-8s %s' % (x['i'], x.get('ptr'), x.get('id'), x.get('f18'),
                                        ('吻合' if x.get('vtOk') else '不吻合'),
                                        (names[k] if names[k] is not None else '(读不出)')))
a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
print('[槽位] %d  [有id] %d  [有名字] %d  [vtable吻合] %d  [id去重] %d  [名字去重] %d' % (len(rows), len(ids), len(valid), vt, uniqIds, uniqNames))
if ids: print('[id 范围] %d .. %d' % (min(ids), max(ids)))
print('')
print('=== 前 40 行 ===')
for k in range(min(40, len(rows))):
    x = rows[k]
    print('    %-6d id=%-8s vt=%-6s %s' % (x['i'], x.get('id'), x.get('vtOk'), names[k]))
print('')
print('=== 第 70..100 行(通用角色) ===')
for k in range(70, min(100, len(rows))):
    x = rows[k]
    print('    %-6d id=%-8s vt=%-6s %s' % (x['i'], x.get('id'), x.get('vtOk'), names[k]))
try: frida.kill(pid)
except Exception: pass