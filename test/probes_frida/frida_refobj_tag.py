# frida_refobj_tag.py -- 检验预测: CReferenceObject 派生类的 +0x08 是国家 tag
#
# 静态证据(CFleet/CCharacter 构造函数):
#   *(_QWORD *)a1        = &CReferenceObject::`vftable';
#   *(_QWORD *)(a1 + 8)  = Invalid_country_tag_0;
# => 基类 CReferenceObject = { vtable(+0x00), CCountryTag tag(+0x08), bool(+0x10) }
#
# 可证伪预测: 任何 CCharacter / CFleet 实例的 +0x08,
#   要么等于初始值 Invalid_country_tag_0,
#   要么是一个合法的 3 字符 tag(第3字节为 0, 前3字节为大写字母/数字)。
# 若出现大量不满足者, 预测即被推翻。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_CHAR = base.add(0x297EA60);
var VT_FLEET = base.add(0x2962A18);
var VT_COUNTRY = base.add(0x27E7360);
var INVALID = base.add(0x333D528);   // Invalid_country_tag_0 的地址(RVA 0x333D528)
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function findObjects(vt, limit) {
    var pat = vt.toMatchPattern();
    var res = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length && res.length < limit; i++) {
        var r = ranges[i];
        if (r.size > 512 * 1024 * 1024) continue;
        var hits;
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < hits.length && res.length < limit; j++) {
            var a = hits[j].address;
            // 判定这是对象头: 该地址必须是可读对象的起点 + 紧邻的 tag 字段也合理
            if (!readable(a, 0x120)) continue;
            res.push(a);
        }
    }
    return res;
}
function tagAt(p) {
    try {
        var b = new Uint8Array(p.readByteArray(4));
        if (b[3] !== 0) return null;
        if (!((b[0] >= 65 && b[0] <= 90) || (b[0] >= 48 && b[0] <= 57))) return null;
        if (!((b[1] >= 65 && b[1] <= 90) || (b[1] >= 48 && b[1] <= 57))) return null;
        if (!((b[2] >= 65 && b[2] <= 90) || (b[2] >= 48 && b[2] <= 57))) return null;
        return String.fromCharCode(b[0], b[1], b[2]);
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var out = {chars: [], fleets: [], charStats: null, fleetStats: null};
    // CCharacter
    var chars = findObjects(VT_CHAR, 400);
    var ok = 0, init = 0, bad = 0; var samples = [];
    for (var i = 0; i < chars.length; i++) {
        var t = tagAt(chars[i].add(8));
        var raw;
        try { raw = chars[i].add(8).readU32(); } catch (e) { raw = 0; }
        if (t) { ok++; if (samples.length < 25) samples.push(t); }
        else if (raw === 0) { init++; }
        else { bad++; if (samples.length < 25) samples.push('[raw=0x' + raw.toString(16) + ']'); }
    }
    out.charStats = {total: chars.length, validTag: ok, zero: init, other: bad, samples: samples};
    // CFleet
    var fleets = findObjects(VT_FLEET, 200);
    var ok2 = 0, init2 = 0, bad2 = 0; var s2 = [];
    for (var i = 0; i < fleets.length; i++) {
        var t2 = tagAt(fleets[i].add(8));
        var raw2;
        try { raw2 = fleets[i].add(8).readU32(); } catch (e) { raw2 = 0; }
        if (t2) { ok2++; if (s2.length < 25) s2.push(t2); }
        else if (raw2 === 0) { init2++; }
        else { bad2++; if (s2.length < 25) s2.push('[raw=0x' + raw2.toString(16) + ']'); }
    }
    out.fleetStats = {total: fleets.length, validTag: ok2, zero: init2, other: bad2, samples: s2};
    // 顺便验证 +0x08 是否等于某个已知 tag (与 tag 数组交叉)
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
for k, label in (('charStats', 'CCharacter'), ('fleetStats', 'CFleet')):
    s = r[k]
    if not s: continue
    print('')
    print('=== %s 实例检验 (预测: +0x08 是 CCountryTag) ===' % label)
    print('    扫描到的对象数 : %d' % s['total'])
    print('    +0x08 是合法tag : %d' % s['validTag'])
    print('    +0x08 为 0      : %d' % s['zero'])
    print('    +0x08 其它      : %d' % s['other'])
    print('    样本: %s' % ' '.join(str(x) for x in s['samples']))
try: frida.kill(pid)
except Exception: pass