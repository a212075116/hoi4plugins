# frida_gs_wide.py -- 把 CGameState 扫描窗口扩到 0x10000, 找 CCharacter/CFleet/CDecision/CEvent
#
# 依据: A 组剩余类不在 CGameState 的 0..0x4000 内, 也不在 CCountry 内。
# CCharacter 实例数 13913, CDecision 167 => 应当是集中的管理数组。
# 判据不变: 元素对象的 vtable 与已知类 RVA 精确相等。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var KNOWN = {
    '0x297ea60': 'CCharacter',
    '0x2962a18': 'CFleet',    '0x2962a70': 'CFleet-b',
    '0x27eb3d0': 'CDecision', '0x27eb3e8': 'CDecision-b', '0x27eb438': 'CDecision-c',
    '0x2999be8': 'CEvent',    '0x2999c40': 'CEvent-b',
    '0x27183a8': 'CGameDate', '0x27183d8': 'CGameDate-b',
    '0x2971b18': 'CProvince', '0x2936cc0': 'CState',  '0x27e7360': 'CCountry'
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
    var out = {gs: gs.toString(), found: [], byType: {}};
    for (var off = 0; off < 0x10000; off += 4) {
        var p = rd(gs.add(off));
        if (!p || p.isNull()) continue;
        var sz = rd32(gs.add(off + 8));
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
            if (key in KNOWN) { samp = {vt: v, cls: KNOWN[key]}; si = i; break; }
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
        out.found.push({off: off, size: sz, cls: samp.cls, firstIdx: si, same: same, valid: valid});
        out.byType[samp.cls] = (out.byType[samp.cls] || 0) + 1;
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
print('[CGameState] %s' % r['gs'])
print('[命中] %d' % len(r['found']))
print('')
print('%-10s %-8s %-14s %-9s %s' % ('偏移', '元素数', '元素类型', '首样本', '一致率'))
print('-' * 64)
for f in r['found']:
    print('+0x%-7x %-8d %-14s %-9d %d/%d' % (f['off'], f['size'], f['cls'], f['firstIdx'], f['same'], f['valid']))
print('')
print('=== 按类型汇总 ===')
for k in sorted(r['byType']):
    print('    %-14s %d 个数组' % (k, r['byType'][k]))
try: frida.kill(pid)
except Exception: pass