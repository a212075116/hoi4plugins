# frida_char_enum.py -- 全量枚举 CCharacter 的 id 与名字
#
# 静态依据(全部来自反汇编, 不是猜测):
#   1) 管理器位置: sub_1410DCDF0 里
#        v24 = *((_QWORD *)Invalid_country_tag + 213);
#        Invalid_country_tag == CGameState::_pInstance
#        断言证实: "_pInstance && \"gamestate unitilialized\""  gamestate.h:1116
#        213 * 8 = 0x6A8  =>  管理器指针在 CGameState + 0x6A8
#   2) 管理器结构: sub_1406B70B0(mgr, src)
#        v3 = *(DWORD*)(mgr+8); *(DWORD*)(mgr+8) = v3+1;   计数器自增
#        v8 = v3;                                            递增的 id
#        sub_1406B2A10(mgr+16, &obj);                        追加进 mgr+0x10 数组
#        *(DWORD*)(mgr+28)                                   元素数
#   3) id: sub_140357BE0 调用点反汇编 mov [rax+18h], edx  =>  CCharacter + 0x18
#   4) 名字: 构造函数 sub_140F9EC50(this, name, id)
#        sub_14011E010(a1 + 72, a2)  =>  CCharacter + 0x48 是 CString
#   5) 大小 0x130 (malloc(0x130))
#
# 等待策略: 轮询 qword_14332F260 非 NULL 且 CProvince 数组可用 —— 绝不用固定 sleep。
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
        var pProv = gs.add(0x2B0).readPointer();
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
    if (out.size === null || out.size > 200000) { out.err = 'size 异常: ' + out.size; return out; }
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
            name: readCS(p.add(0x48))
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

# 轮询等状态就绪(不用固定 sleep)
t0 = time.time()
last = None
while time.time() - t0 < 300:
    try:
        st = sc.exports_sync.ready()
    except Exception as e:
        st = {'ok': False, 'why': 'rpc: %s' % e}
    if st.get('ok'):
        print('[就绪] %s' % st, flush=True)
        break
    if st.get('why') != last:
        print('  等待中: %s' % st.get('why'), flush=True)
        last = st.get('why')
    time.sleep(1)
else:
    print('[超时] 状态未就绪')
    frida.kill(pid); raise SystemExit(1)

r = sc.exports_sync.run()
print('')
print('hoi4.exe 基址   : %s' % r['base'])
print('CGameState*     : %s' % r['gs'])
print('管理器 (+0x6A8) : %s' % r.get('mgr'))
if r.get('err'): print('错误: %s' % r['err'])
print('计数器(+8)      : %s' % r.get('counter'))
print('数组指针(+0x10) : %s' % r.get('arrPtr'))
print('元素数(+0x1c)   : %s' % r.get('size'))
rows = r.get('rows') or []
if rows:
    n = sum(1 for x in rows if x.get('id') is not None)
    nm = sum(1 for x in rows if x.get('name'))
    vt = sum(1 for x in rows if x.get('vtOk'))
    print('')
    print('有 id 的项  : %d / %d' % (n, len(rows)))
    print('有名字的项  : %d / %d' % (nm, len(rows)))
    print('vtable 吻合 : %d / %d' % (vt, len(rows)))
    print('')
    print('=== 样本(前 30) ===')
    for x in rows[:30]:
        if x.get('null'): print('    %-6d (NULL)' % x['i']); continue
        if x.get('unreadable'): print('    %-6d %s (不可读)' % (x['i'], x.get('ptr'))); continue
        if x.get('err'): print('    %-6d (%s)' % (x['i'], x['err'])); continue
        print('    %-6d ptr=%-20s id=%-8s vtOk=%-6s name=%r' % (x['i'], x.get('ptr'), x.get('id'), x.get('vtOk'), (x.get('name') or '')[:45]))
try: frida.kill(pid)
except Exception: pass