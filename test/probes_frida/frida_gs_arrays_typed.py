# frida_gs_arrays_typed.py -- 用 vtable 指纹识别 CGameState 里所有数组的元素类型
#
# 方法(与验证 CCountry 数组时同一个, 已被证明可靠):
#   候选数组 = (base, size), 判据是 base 可读且 size 合理
#   元素类型 = 读首元素的 vtable, 与已知类的 vtable RVA 精确比对
#   绝不用"看起来像指针"做判据 —— 那个方法此前已被证明会导致误判。
#
# A 组 9 个类的 vtable RVA 全部来自 IDA 的 RTTI 恢复(12333 个虚表)。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var KNOWN = {
    '0x27e7360': 'CCountry',
    '0x2936cc0': 'CState',   '0x2936d10': 'CState(2)',
    '0x2971b18': 'CProvince','0x2971b68': 'CProvince(2)',
    '0x297ea60': 'CCharacter',
    '0x2962a18': 'CFleet',   '0x2962a70': 'CFleet(2)',
    '0x27eb3d0': 'CDecision','0x27eb3e8': 'CDecision(2)','0x27eb438': 'CDecision(3)',
    '0x2999be8': 'CEvent',   '0x2999c40': 'CEvent(2)',
    '0x27183a8': 'CGameDate','0x27183d8': 'CGameDate(2)',
    '0x27210e0': 'CGameState','0x2721138': 'CGameState(2)'
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
    var out = {gs: gs.toString(), found: []};
    for (var off = 0; off < 0x1000; off += 4) {
        var p = rd(gs.add(off));
        if (!p || p.isNull()) continue;
        var sz = rd32(gs.add(off + 8));
        if (sz === null || sz <= 0 || sz > 20000) continue;
        if (!readable(p, 8)) continue;
        // 试两种元素宽度: 8 字节(指针数组)
        var el = rd(p);
        if (!el || el.isNull() || !readable(el, 16)) continue;
        var vt = rd(el);
        if (!vt) continue;
        var rva = vt.sub(base);
        var key = '0x' + rva.toString(16);
        if (!(key in KNOWN)) continue;
        // 统计这一数组里首元素类型在多少项上成立
        var same = 0, checked = Math.min(sz, 40);
        for (var i = 0; i < checked; i++) {
            var e2 = rd(p.add(i * 8));
            if (!e2 || e2.isNull() || !readable(e2, 8)) continue;
            var v2 = rd(e2);
            if (v2 && v2.equals(vt)) same++;
        }
        out.found.push({off: off, ptr: p.toString(), size: sz, cls: KNOWN[key], rva: key, same: same, checked: checked});
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
print('[识别出的数组] %d 个' % len(r['found']))
print('')
print('%-10s %-32s %-8s %-14s %s' % ('偏移', '数组基址', '元素数', '元素类型', '首元素类型一致率'))
print('-' * 92)
for f in r['found']:
    print('+0x%-7x %-32s %-8d %-14s %d/%d' % (f['off'], f['ptr'], f['size'], f['cls'], f['same'], f['checked']))
try: frida.kill(pid)
except Exception: pass