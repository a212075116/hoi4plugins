# frida_gs_arrays2.py -- 修正"元素0为NULL"的假设, 扫更大范围识别 A 组数组
#
# 上一版漏检原因: 直接读元素0当样本, 而 CProvince/CState/CCountry 数组的索引0 都是 NULL。
# 本版: 在每 8 字节槽里找第一个非 NULL 且可读的元素作为类型样本。
# 同时把扫描范围从 0x1000 扩到 0x4000。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var KNOWN = {
    '0x27e7360': 'CCountry',
    '0x2936cc0': 'CState',   '0x2936d10': 'CState-b',
    '0x2971b18': 'CProvince','0x2971b68': 'CProvince-b',
    '0x297ea60': 'CCharacter',
    '0x2962a18': 'CFleet',   '0x2962a70': 'CFleet-b',
    '0x27eb3d0': 'CDecision','0x27eb3e8': 'CDecision-b','0x27eb438': 'CDecision-c',
    '0x2999be8': 'CEvent',   '0x2999c40': 'CEvent-b',
    '0x27183a8': 'CGameDate','0x27183d8': 'CGameDate-b',
    '0x27210e0': 'CGameState','0x2721138': 'CGameState-b'
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
    var out = {gs: gs.toString(), found: [], nullCount: {}};
    for (var off = 0; off < 0x4000; off += 4) {
        var p = rd(gs.add(off));
        if (!p || p.isNull()) continue;
        var sz = rd32(gs.add(off + 8));
        if (sz === null || sz <= 0 || sz > 40000) continue;
        if (!readable(p, 16)) continue;
        // 找第一个可用样本(跳过 NULL) —— 这是上一版漏检的根因
        var samp = null, sampIdx = -1;
        var probe = Math.min(sz, 60);
        for (var i = 0; i < probe; i++) {
            var e = rd(p.add(i * 8));
            if (!e || e.isNull() || !readable(e, 16)) continue;
            var v = rd(e);
            if (!v || v.isNull()) continue;
            var rva = v.sub(base);
            var key = '0x' + rva.toString(16);
            if (key in KNOWN) { samp = {i: i, vt: v, cls: KNOWN[key], key: key}; sampIdx = i; break; }
        }
        if (!samp) continue;
        // 统计一致率
        var same = 0, valid = 0;
        for (var i = 0; i < probe; i++) {
            var e2 = rd(p.add(i * 8));
            if (!e2 || e2.isNull() || !readable(e2, 8)) continue;
            var v2 = rd(e2);
            if (!v2) continue;
            valid++;
            if (v2.equals(samp.vt)) same++;
        }
        out.found.push({off: off, ptr: p.toString(), size: sz, cls: samp.cls, firstIdx: sampIdx, same: same, valid: valid});
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
print('[识别出的 A 组数组] %d 个' % len(r['found']))
print('')
print('%-10s %-8s %-14s %-9s %s' % ('偏移', '元素数', '元素类型', '首个有效下标', '类型一致率'))
print('-' * 70)
for f in r['found']:
    print('+0x%-7x %-8d %-14s %-9d %d/%d' % (f['off'], f['size'], f['cls'], f['firstIdx'], f['same'], f['valid']))
try: frida.kill(pid)
except Exception: pass