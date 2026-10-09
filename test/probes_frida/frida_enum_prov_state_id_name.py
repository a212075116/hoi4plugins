# frida_enum_prov_state_id_name.py -- 全量输出 CProvince / CState 的 id 与名字
#
# 目的: 用户要求拿出 id 和名字, 以证明这些对象确实是 Province / State。
# 静态依据:
#   CProvince 构造函数 sub_140E78EC0: *(_DWORD *)(a1 + 164) = *(_DWORD *)(a2 + 196);
#     164 = 0xA4, 故 a1+0xA4 是 id
#   CState 构造函数 sub_1409CFB10: a1[10] = 15LL -> a1+0x50 是 CString capacity(15),
#     说明 0x40 起是 CString; 侦察显示 a1+0x58 是随下标递增的整数
#
# 本脚本全量遍历, 每项输出: 下标 / 对象指针 / id(+0xA4 与 +0x58) / 名字候选 / 相邻字段,
# 不过滤任何项。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CProvince_CState_id与名字完整枚举.txt'

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
function readCString(p) {
    try {
        var cap = Number(p.add(24).readU64());
        var sz  = Number(p.add(16).readU64());
        if (sz === 0 || sz > 400 || cap > 400 || cap < sz) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) s += String.fromCharCode(dp.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
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
        out.prov.rows.push({
            i: i, ptr: p.toString(),
            id_a4: u32(p, 0xa4), id_1fc: u32(p, 0x1fc),
            name_40: readCString(p.add(0x40)),
            s58: u32(p, 0x58),
            owner: u32(p, 0xac),
            controller: u32(p, 0xc4)
        });
    }
    for (var i = 0; i < sState; i++) {
        var p;
        try { p = pState.add(i * 8).readPointer(); } catch (e) { out.state.rows.push({i: i, err: 'slot'}); continue; }
        if (p.isNull()) { out.state.rows.push({i: i, null: true}); continue; }
        if (!readable(p, 0x200)) { out.state.rows.push({i: i, ptr: p.toString(), unreadable: true}); continue; }
        out.state.rows.push({
            i: i, ptr: p.toString(),
            id_58: u32(p, 0x58), id_18c: u32(p, 0x18c),
            name_40: readCString(p.add(0x40)),
            a20: u32(p, 0x20), a24: u32(p, 0x24),
            provCount: u32(p, 0x68)
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
time.sleep(8)
r = sc.exports_sync.run()

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : hoi4.exe (游戏根目录)')
a('访问方式     : Frida, 静态锚点 qword_14332F260 -> CGameState')
a('涉及类       : CGameState -> CProvince / CState')
a('涉及函数     : CProvince::ctor sub_140E78EC0 / CState::ctor sub_1409CFB10 (静态依据来源)')
a('测试目的     : 用 id 与名字证明这些对象确实是 CProvince / CState')
a('完整性问题   : 全量输出, 不抽样, 不过滤')
a('')
a('静态依据:')
a('  CProvince ctor: *(_DWORD*)(a1 + 164) = *(_DWORD*)(a2 + 196);   164 = 0xA4 => id 在 +0xA4')
a('  CState    ctor: a1[10] = 15LL  => +0x50 是 CString capacity, 故 +0x40 起是该 CString')
a('')
a('hoi4.exe 基址: %s' % r['base'])
a('CGameState*  : %s' % r['gs'])
a('')

for key, label in (('prov', 'CProvince'), ('state', 'CState')):
    d = r[key]
    rows = d['rows']
    a('=' * 110)
    a('%s 数组  基址=%s  声明元素数=%d' % (label, d['ptr'], d['size']))
    a('=' * 110)
    # 统计
    idk = 'id_a4' if key == 'prov' else 'id_58'
    nId = 0; nMatch = 0; nZeros = 0; nName = 0
    for x in rows:
        v = x.get(idk)
        if v is None: continue
        nId += 1
        if v == x['i']: nMatch += 1
        if v == 0: nZeros += 1
        if x.get('name_40'): nName += 1
    a('')
    a('统计:')
    a('    总项数                 : %d' % len(rows))
    a('    有 id 值的项            : %d' % nId)
    a('    其中 id == 数组下标     : %d' % nMatch)
    a('    其中 id == 0            : %d' % nZeros)
    a('    名字字段非空的项        : %d' % nName)
    a('')
    a('-' * 110)
    if key == 'prov':
        a('%-8s %-20s %-10s %-10s %-26s %-10s %-10s' % ('下标', '对象指针', 'id(+A4)', 'id(+1FC)', '名字(+40)', 'owner', 'ctrl'))
    else:
        a('%-8s %-20s %-10s %-10s %-26s %-10s %-10s' % ('下标', '对象指针', 'id(+58)', 'id(+18C)', '名字(+40)', '+20', '+24'))
    a('-' * 110)
    for x in rows:
        if x.get('null'):
            a('%-8d %-20s %-10s %-10s %-26s %-10s %-10s' % (x['i'], '0x0', '-', '-', '(NULL)', '-', '-'))
            continue
        if x.get('unreadable'):
            a('%-8d %-20s %-10s %-10s %-26s %-10s %-10s' % (x['i'], x.get('ptr','?'), '-', '-', '(不可读)', '-', '-'))
            continue
        if x.get('err'):
            a('%-8d %-20s %-10s %-10s %-26s %-10s %-10s' % (x['i'], '-', '-', '-', '(slot 读取失败)', '-', '-'))
            continue
        if key == 'prov':
            a('%-8d %-20s %-10s %-10s %-26s %-10s %-10s' % (
                x['i'], x['ptr'], x.get('id_a4'), x.get('id_1fc'),
                (x.get('name_40') or '(空)'), x.get('owner'), x.get('controller')))
        else:
            a('%-8d %-20s %-10s %-10s %-26s %-10s %-10s' % (
                x['i'], x['ptr'], x.get('id_58'), x.get('id_18c'),
                (x.get('name_40') or '(空)'), x.get('a20'), x.get('a24')))
    a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
for key, label, idk in (('prov', 'CProvince', 'id_a4'), ('state', 'CState', 'id_58')):
    rows = r[key]['rows']
    n = sum(1 for x in rows if x.get(idk) is not None)
    m = sum(1 for x in rows if x.get(idk) is not None and x[idk] == x['i'])
    nm = sum(1 for x in rows if x.get('name_40'))
    print('[%s] 总=%d  有id=%d  id==下标=%d  有名字=%d' % (label, len(rows), n, m, nm))
try: frida.kill(pid)
except Exception: pass