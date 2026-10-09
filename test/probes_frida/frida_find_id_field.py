# frida_find_id_field.py -- 在 CProvince / CState 对象里找 id 字段
#
# 背景: 用户要求拿出名字和 id, 单靠 vtable 相等不构成"这是 Province/State"的证明。
# 静态线索:
#   CProvince 构造函数: *(_DWORD*)(a1 + 164) = *(_DWORD*)(a2 + 196);  <-- 候选 id
#   CState  断言里出现 "... with id: "
#
# 做法(两步):
#   步骤1 侦察: dump 少量对象的原始字节, 找出值为 1..N 连续整数的候选偏移
#   步骤2 全量: 对候选偏移逐个全量校验(每个对象都要满足唯一且连续)
# 本脚本只做步骤1, 并把候选偏移列出来。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
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
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {prov: {}, state: {}};
    function scan4(ptr, size, tag) {
        // 侦察: 取前 6 个对象, 对每个 4 字节对齐偏移, 看在多少个对象上落在 1..size 范围
        var objs = [];
        for (var i = 1; i <= 6; i++) {
            var p;
            try { p = ptr.add(i * 8).readPointer(); } catch (e) { break; }
            if (!p.isNull() && readable(p, 0x300)) objs.push({i: i, p: p});
        }
        var cands = [];
        for (var off = 0; off < 0x300; off += 4) {
            var vals = [];
            var ok = 0;
            for (var k = 0; k < objs.length; k++) {
                var v;
                try { v = objs[k].p.add(off).readU32(); } catch (e) { v = null; }
                vals.push(v);
                if (v !== null && v >= 1 && v <= size) ok++;
            }
            if (ok === objs.length) cands.push({off: off, vals: vals});
        }
        return {objCount: objs.length, sampleIdx: objs.map(function (o) { return o.i; }), cands: cands.slice(0, 30)};
    }
    var pProv = gs.add(0x2B0).readPointer();
    var sProv = gs.add(0x2B0).add(8).readU32();
    var pState = gs.add(0x2C8).readPointer();
    var sState = gs.add(0x2C8).add(8).readU32();
    out.prov = scan4(pProv, sProv, 'CProvince');
    out.prov.size = sProv; out.prov.ptr = pProv.toString();
    out.state = scan4(pState, sState, 'CState');
    out.state.size = sState; out.state.ptr = pState.toString();
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
for key, label in (('prov', 'CProvince'), ('state', 'CState')):
    d = r[key]
    print('')
    print('=== %s  id 候选偏移侦察 (元素数=%d) ===' % (label, d['size']))
    print('    取样对象: 下标 %s' % d['sampleIdx'])
    print('    候选偏移(在所有取样对象上值都落在 1..%d): %d 个' % (d['size'], len(d['cands'])))
    for c in d['cands']:
        print('        +0x%-4x 值=%s' % (c['off'], c['vals']))
try: frida.kill(pid)
except Exception: pass