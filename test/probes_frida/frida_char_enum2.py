# frida_char_enum2.py -- 全量枚举 CCharacter 的 id 与名字, 并写出完整文件
#
# 静态依据(全部来自反汇编):
#   管理器: CGameState + 0x6A8
#     来源 sub_1410DCDF0: v24 = *((_QWORD *)Invalid_country_tag + 213); 213*8 = 0x6A8
#     Invalid_country_tag == CGameState::_pInstance
#     断言证实: "_pInstance && \"gamestate unitilialized\"" @ gamestate.h:1116
#   管理器结构 sub_1406B70B0(mgr, src):
#     +8  计数器(下一个 id)
#     +0x10 数组数据指针   +0x1c 元素数   (sub_1406B2A10 追加)
#   id 字段: sub_140357BE0 调用点 mov [rax+18h], edx  => CCharacter + 0x18
#   名字: 构造函数 sub_140F9EC50(this, name, id) 里 sub_14011E010(a1+72, a2) => +0x48
#   大小 0x130
#
# 等待: 轮询就绪, 不用固定 sleep。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CCharacter_id与名字完整枚举.txt'

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
function readCS(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz > 300 || cap < sz || cap > 300) return null;
        if (sz === 0) return '';
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) s += String.fromCharCode(dp.add(i).readU8());
        return s;
    } catch (e) { return null; }
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.ready = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull()) return {ok: false, why: 'GS NULL'};
        if (!readable(gs, 0x800)) return {ok: false, why: 'GS 不可读'};
        var sProv = gs.add(0x2B0).add(8).readU32();
        if (sProv < 9000) return {ok: false, why: 'CProvince size=' + sProv};
        var mgr = gs.add(0x6A8).readPointer();
        if (mgr.isNull() || !readable(mgr, 0x40)) return {ok: false, why: 'mgr 不可读'};
        var sz = u32(mgr, 0x1c);
        if (sz === null || sz === 0) return {ok: false, why: 'mgr size=' + sz};
        return {ok: true, provSize: sProv, mgrSize: sz, mgr: mgr.toString()};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {base: base.toString(), gs: gs.toString()};
    var mgr = gs.add(0x6A8).readPointer();
    out.mgr = mgr.toString();
    out.counter = u32(mgr, 8);
    var arr = mgr.add(0x10).readPointer();
    out.arrPtr = arr.toString();
    out.size = u32(mgr, 0x1c);
    out.rows = [];
    for (var i = 0; i < out.size; i++) {
        var p;
        try { p = arr.add(i * 8).readPointer(); } catch (e) { out.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x130)) { out.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        var vt = null;
        try { vt = p.readPointer(); } catch (e) {}
        out.rows.push({
            i: i, ptr: p.toString(),
            vtOk: (vt && vt.equals(VT_CHAR)),
            id: u32(p, 0x18),
            id70: u32(p, 0x70),
            name: readCS(p.add(0x48)),
            name28: readCS(p.add(0x28))
        });
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
t0 = time.time()
last = None
while time.time() - t0 < 300:
    try: st = sc.exports_sync.ready()
    except Exception as e: st = {'ok': False, 'why': 'rpc: %s' % e}
    if st.get('ok'):
        print('[就绪] %s' % st, flush=True); break
    if st.get('why') != last:
        print('  等待中: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    print('[超时]'); frida.kill(pid); raise SystemExit(1)

r = sc.exports_sync.run()
rows = r.get('rows') or []

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : hoi4.exe (游戏根目录)')
a('访问方式     : Frida, 静态锚点 qword_14332F260 -> CGameState')
a('涉及类       : CGameState -> CCharacter')
a('涉及函数     : CCharacter::ctor sub_140F9EC50')
a('               CCharacter 创建 sub_1406B70B0 / sub_1406B7510')
a('               上层 sub_1410DCDF0 / sub_140357BE0')
a('测试目的     : 拿出 CCharacter 的 id 与名字')
a('完整性问题   : 全量输出, 不抽样, 不过滤')
a('')
a('判据链(每条的依据都来自反汇编):')
a('  1. 管理器位置  CGameState + 0x6A8')
a('     sub_1410DCDF0 里: v24 = *((_QWORD *)Invalid_country_tag + 213);  213*8 = 0x6A8')
a('     Invalid_country_tag 即 CGameState::_pInstance,')
a('     由断言 \"_pInstance && gamestate unitilialized\" (gamestate.h:1116) 证实')
a('  2. 管理器结构  sub_1406B70B0(mgr, src):')
a('     +0x08 计数器(下一个 id)   +0x10 数组数据   +0x1C 元素数')
a('     sub_1406B2A10(mgr+16, &obj) 把新对象追加进数组')
a('  3. id 字段  CCharacter + 0x18')
a('     sub_140357BE0 调用点反汇编: mov edx, [rbp+arg_18] ; mov [rax+18h], edx')
a('  4. 名字字段  CCharacter + 0x48')
a('     构造函数 sub_140F9EC50(this, name, id) 里 sub_14011E010(a1 + 72, a2)')
a('  5. 对象大小  0x130  (sub_1406B70B0 / sub_140FA0A20 里的 malloc(0x130))')
a('  6. 虚表  CCharacter @ RVA 0x297EA60')
a('')
a('等待策略: 轮询 qword_14332F260 非 NULL 且 CProvince 数组 size>=9000 且管理器可用,')
a('          全程不使用固定 sleep。')
a('')
a('hoi4.exe 基址   : %s' % r['base'])
a('CGameState*     : %s' % r['gs'])
a('管理器 (+0x6A8) : %s' % r.get('mgr'))
a('计数器(+0x08)   : %s' % r.get('counter'))
a('数组指针(+0x10) : %s' % r.get('arrPtr'))
a('元素数(+0x1C)   : %s' % r.get('size'))
a('')

n = sum(1 for x in rows if x.get('id') is not None)
nm = sum(1 for x in rows if x.get('name'))
vt = sum(1 for x in rows if x.get('vtOk'))
ids = [x['id'] for x in rows if x.get('id') is not None]
uniq = len(set(ids))
a('统计:')
a('    总项数        : %d' % len(rows))
a('    有 id 的项    : %d' % n)
a('    有名字的项    : %d' % nm)
a('    vtable 吻合项 : %d' % vt)
a('    id 去重后     : %d' % uniq)
if ids:
    a('    id 最小值     : %d' % min(ids))
    a('    id 最大值     : %d' % max(ids))
a('')
a('=' * 118)
a('%-8s %-20s %-10s %-10s %-8s %s' % ('下标', '对象指针', 'id(+18)', '(+70)', 'vtable', '名字(+48)'))
a('=' * 118)
for x in rows:
    if x.get('null'):
        a('%-8d %-20s %-10s %-10s %-8s %s' % (x['i'], '0x0', '-', '-', '-', '(NULL 空槽)')); continue
    if x.get('unreadable'):
        a('%-8d %-20s %-10s %-10s %-8s %s' % (x['i'], x.get('ptr'), '-', '-', '-', '(指针不可读)')); continue
    if x.get('err'):
        a('%-8d %-20s %-10s %-10s %-8s %s' % (x['i'], '-', '-', '-', '-', '(slot 读取失败)')); continue
    a('%-8d %-20s %-10s %-10s %-8s %s' % (x['i'], x.get('ptr'), x.get('id'), x.get('id70'),
                                          ('吻合' if x.get('vtOk') else '不吻合'),
                                          (x.get('name') if x.get('name') is not None else '(读不出)')))
a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('')
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
print('[总项] %d  [有id] %d  [有名字] %d  [vtable吻合] %d  [id去重] %d' % (len(rows), n, nm, vt, uniq))
if ids: print('[id 范围] %d .. %d' % (min(ids), max(ids)))
print('')
print('=== 全部名字(前 60) ===')
cs = [x.get('name') for x in rows if x.get('name')]
for k in range(0, min(60, len(cs)), 4):
    print('    ' + '  '.join('%-26s' % v for v in cs[k:k+4]))
try: frida.kill(pid)
except Exception: pass