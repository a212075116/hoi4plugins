# frida_enum_prov_state.py -- 完整枚举 CGameState+0x2B0 与 +0x2C8 的全部实例(不抽样)
#
# 目的: 确认 +0x2B0 是 CProvince* 数组, +0x2C8 是 CState* 数组。
# 要求: 完整输出每一个元素, 不过滤 NULL / 不可读 / 不匹配的项。
#
# 判据: 元素对象的 vtable 是否精确等于已知类虚表地址。
#   CProvince 虚表 RVA 0x2971B18 (另有 0x2971B68)
#   CState    虚表 RVA 0x2936CC0 (另有 0x2936D10)
# 每个元素都给出: 下标 / 指针 / vtable RVA / 是否匹配 / 原始 8 字节。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CProvince_CState_完整枚举.txt'

JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_PROV = [base.add(0x2971B18), base.add(0x2971B68)];
var VT_STATE = [base.add(0x2936CC0), base.add(0x2936D10)];
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function dumpArray(arrPtr, size, vts, name) {
    var rows = [];
    for (var i = 0; i < size; i++) {
        var slot = arrPtr.add(i * 8);
        var raw;
        try { raw = slot.readPointer(); } catch (e) { rows.push({i: i, err: 'slot-unreadable'}); continue; }
        if (raw.isNull()) { rows.push({i: i, ptr: '0x0', verdict: 'NULL'}); continue; }
        if (!readable(raw, 16)) { rows.push({i: i, ptr: raw.toString(), verdict: 'unreadable'}); continue; }
        var vt;
        try { vt = raw.readPointer(); } catch (e) { rows.push({i: i, ptr: raw.toString(), verdict: 'vt-unreadable'}); continue; }
        var rva = vt.sub(base);
        var match = null;
        for (var k = 0; k < vts.length; k++) if (vt.equals(vts[k])) match = k;
        rows.push({
            i: i,
            ptr: raw.toString(),
            vtRva: '0x' + rva.toString(16),
            verdict: (match === null ? 'MISMATCH' : 'MATCH'),
            vtIdx: match
        });
    }
    return rows;
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), base: base.toString(), prov: null, state: null};
    var pProv = gs.add(0x2B0).readPointer();
    var sProv = gs.add(0x2B0).add(8).readU32();
    var pState = gs.add(0x2C8).readPointer();
    var sState = gs.add(0x2C8).add(8).readU32();
    out.prov = {ptr: pProv.toString(), size: sProv, rows: dumpArray(pProv, sProv, VT_PROV, 'CProvince')};
    out.state = {ptr: pState.toString(), size: sState, rows: dumpArray(pState, sState, VT_STATE, 'CState')};
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
def a(s): L.append(s)
a('时间戳       : 20261009_015321')
a('测试模块     : hoi4.exe (游戏根目录)')
a('访问方式     : Frida, CGameState 静态锚点 qword_14332F260 (RVA 0x332F260)')
a('涉及类       : CGameState -> CProvince / CState')
a('涉及函数     : 无(仅内存读取), 判据为 vtable 精确相等')
a('测试目的     : 确认 CGameState+0x2B0 是 CProvince* 数组, +0x2C8 是 CState* 数组')
a('完整性问题   : 全量输出, 不抽样, 不过滤 NULL/不可读/不匹配项')
a('')
a('=' * 100)
a('运行环境')
a('=' * 100)
a('hoi4.exe 基址        : %s' % r['base'])
a('CGameState*          : %s' % r['gs'])
a('CProvince 虚表 RVA    : 0x2971B18 / 0x2971B68')
a('CState    虚表 RVA    : 0x2936CC0 / 0x2936D10')
a('')

for key, label, vts in (('prov', 'CProvince', '0x2971B18 / 0x2971B68'), ('state', 'CState', '0x2936CC0 / 0x2936D10')):
    d = r[key]
    rows = d['rows']
    a('=' * 100)
    a('%s 数组  基址=%s  声明元素数=%d' % (label, d['ptr'], d['size']))
    a('判据虚表: %s' % vts)
    a('=' * 100)
    from collections import Counter
    c = Counter(x['verdict'] for x in rows)
    a('')
    a('统计: 总项数=%d' % len(rows))
    for k in sorted(c):
        a('    %-16s %d' % (k, c[k]))
    a('')
    a('-' * 100)
    a('%-8s %-20s %-12s %-10s %s' % ('下标', '对象指针', 'vtable RVA', '判定', '说明'))
    a('-' * 100)
    for x in rows:
        if 'err' in x:
            a('%-8d %-20s %-12s %-10s %s' % (x['i'], '-', '-', 'ERR', x['err']))
        elif x['verdict'] == 'NULL':
            a('%-8d %-20s %-12s %-10s %s' % (x['i'], x['ptr'], '-', 'NULL', '空指针'))
        elif x['verdict'] == 'MATCH':
            a('%-8d %-20s %-12s %-10s %s' % (x['i'], x['ptr'], x['vtRva'], 'MATCH', 'vtIdx=%d' % x['vtIdx']))
        else:
            a('%-8d %-20s %-12s %-10s %s' % (x['i'], x['ptr'], x.get('vtRva', '-'), x['verdict'], ''))
    a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))

print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
for key, label in (('prov', 'CProvince'), ('state', 'CState')):
    from collections import Counter
    c = Counter(x['verdict'] for x in r[key]['rows'])
    print('[%s] 总=%d  %s' % (label, len(r[key]['rows']), dict(c)))
try: frida.kill(pid)
except Exception: pass