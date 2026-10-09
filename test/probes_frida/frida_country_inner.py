# frida_country_inner.py -- 在 CCountry 实例内部找 CCharacter/CFleet/CDecision 等数组
#
# 依据: A 组剩余 5 个类(CCharacter/CFleet/CDecision/CEvent/CGameDate)不在 CGameState 顶层数组里。
# CCharacter 实例数 13913 而 CCountry 只有 133 个 => 角色极可能按国家分列表存放在 CCountry 内。
#
# 方法沿用已验证的那套纯判据:
#   候选 = (ptr, size) 且 ptr 可读, size 合理
#   元素类型 = 元素对象的 vtable 与已知类 RVA 精确相等(不是"看起来像")
#   样本 = 跳过 NULL, 取第一个可用者
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_COUNTRY = base.add(0x27E7360);
var KNOWN = {
    '0x297ea60': 'CCharacter',
    '0x2962a18': 'CFleet',    '0x2962a70': 'CFleet-b',
    '0x27eb3d0': 'CDecision', '0x27eb3e8': 'CDecision-b', '0x27eb438': 'CDecision-c',
    '0x2999be8': 'CEvent',    '0x2999c40': 'CEvent-b',
    '0x27183a8': 'CGameDate', '0x27183d8': 'CGameDate-b',
    '0x2971b18': 'CProvince', '0x2936cc0': 'CState',
    '0x2952b0': 'CArmy?', '0x295a2b0': 'CArmy'
};
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function rd(p) { try { return p.readPointer(); } catch (e) { return null; } }
function rd32(p) { try { return p.readU32(); } catch (e) { return null; } }
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = rd(gs.add(0x310));
    var out = {gs: gs.toString(), byCountry: [], summary: {}};
    // 只看前 6 个国家, 足够看出模式; 每个国家扫 0..0x1710
    for (var ci = 1; ci <= 6; ci++) {
        var cp = rd(carr.add(ci * 8));
        if (!cp || cp.isNull() || !readable(cp, 0x1710)) continue;
        var vt = rd(cp);
        if (!vt || !vt.equals(VT_COUNTRY)) continue;
        var rec = {ci: ci, ptr: cp.toString(), hits: []};
        for (var off = 0; off < 0x1710; off += 4) {
            var p = rd(cp.add(off));
            if (!p || p.isNull()) continue;
            var sz = rd32(cp.add(off + 8));
            if (sz === null || sz <= 0 || sz > 40000) continue;
            if (!readable(p, 8)) continue;
            var samp = null, si = -1;
            var probe = Math.min(sz, 40);
            for (var i = 0; i < probe; i++) {
                var e = rd(p.add(i * 8));
                if (!e || e.isNull() || !readable(e, 16)) continue;
                var v = rd(e);
                if (!v || v.isNull()) continue;
                var key = '0x' + v.sub(base).toString(16);
                if (key in KNOWN) { samp = {vt: v, cls: KNOWN[key], key: key}; si = i; break; }
            }
            if (!samp) continue;
            var same = 0, valid = 0;
            for (var i = 0; i < probe; i++) {
                var e2 = rd(p.add(i * 8));
                if (!e2 || e2.isNull() || !readable(e2, 8)) continue;
                var v2 = rd(e2);
                if (!v2) continue;
                valid++;
                if (v2.equals(samp.vt)) same++;
            }
            rec.hits.push({off: off, size: sz, cls: samp.cls, firstIdx: si, same: same, valid: valid});
            var k = samp.cls + '@0x' + off.toString(16);
            out.summary[k] = (out.summary[k] || 0) + 1;
        }
        out.byCountry.push(rec);
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
for rec in r['byCountry']:
    print('')
    print('=== CCountry #%d @ %s ===' % (rec['ci'], rec['ptr']))
    if not rec['hits']:
        print('    (未发现已知类型的数组)')
        continue
    for h in rec['hits']:
        print('    +0x%-5x size=%-6d %-12s 首样本下标=%-3d 一致率=%d/%d' % (
            h['off'], h['size'], h['cls'], h['firstIdx'], h['same'], h['valid']))
print('')
print('=== 跨国家汇总(类型@偏移 -> 出现在几个国家里) ===')
for k in sorted(r['summary'], key=lambda x: -r['summary'][x]):
    print('    %-28s %d' % (k, r['summary'][k]))
try: frida.kill(pid)
except Exception: pass