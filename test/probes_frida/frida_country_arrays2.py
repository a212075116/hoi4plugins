# frida_country_arrays2.py -- 验证 size=133 的数组, 修正性能问题
#
# 上一版卡死原因: readable() 每次调用都 Process.enumerateRanges(), 而数组最大 9975 项 => O(n^2)。
# 本版: 区间列表只取一次并缓存; 且只处理 size==133 的数组。
#
# 同时验证 tag 数组: 依据 IDA 反编译 sub_14071BD10(countrydatabase.cpp:89),
#   *(_QWORD*)(db + 48) = tag 数组基址
#   *(_DWORD*)(db + 60) = tag 数组大小
#   元素宽 4 字节 => tag 很可能就是原地存的 "ABY+00"
# 因此直接搜 41 42 59 00 (ABY 后跟 NUL) 能排除此前所有字符串池误命中。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_COUNTRY = base.add(0x27E7360);
var OFFS = [0x310, 0x370, 0x388, 0x880];
var RANGES = null;
function loadRanges() {
    if (RANGES) return RANGES;
    RANGES = Process.enumerateRanges('r--');
    return RANGES;
}
function readable(p, n) {
    var rs = loadRanges();
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dp.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), arrs: [], aby: []};
    for (var k = 0; k < OFFS.length; k++) {
        var off = OFFS[k];
        var rec = {off: off, isCountry: 0, other: 0, samples: []};
        var p, sz;
        try { p = gs.add(off).readPointer(); sz = gs.add(off + 8).readU32(); } catch (e) { continue; }
        rec.ptr = p.toString(); rec.size = sz;
        if (sz !== 133) { out.arrs.push(rec); continue; }
        for (var i = 0; i < sz; i++) {
            var el;
            try { el = p.add(i * 8).readPointer(); } catch (e) { break; }
            if (el.isNull()) { rec.other++; continue; }
            var vt;
            try { vt = el.readPointer(); } catch (e) { rec.other++; continue; }
            if (vt.equals(VT_COUNTRY)) {
                rec.isCountry++;
                if (rec.samples.length < 5) {
                    rec.samples.push({i: i, name: readCString(el.add(0x10)), idx: el.add(8).readU32()});
                }
            } else {
                rec.other++;
                if (rec.samples.length < 5) {
                    rec.samples.push({i: i, vt: '0x' + vt.sub(base).toString(16)});
                }
            }
        }
        out.arrs.push(rec);
    }
    // 搜 4 字节 tag 模式: ABY+00 / GEH+00 / HYA+00
    var pats = {'ABY': '41 42 59 00', 'GEH': '47 45 48 00', 'HYA': '48 59 41 00'};
    var names = Object.keys(pats);
    for (var n = 0; n < names.length; n++) {
        var nm = names[n];
        var found = [];
        var rs = loadRanges();
        for (var i = 0; i < rs.length && found.length < 60; i++) {
            var r = rs[i];
            if (r.size > 64 * 1024 * 1024) continue;
            var res;
            try { res = Memory.scanSync(r.base, r.size, pats[nm]); } catch (e) { continue; }
            for (var j = 0; j < res.length && found.length < 60; j++) found.push(res[j].address.toString());
        }
        out.aby.push({tag: nm, n: found.length, addrs: found.slice(0, 25)});
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
time.sleep(6)
r = sc.exports_sync.run()
print('[CGameState] %s' % r['gs'])
print('')
print('[size=133 的数组]')
for a in r['arrs']:
    if 'size' not in a: continue
    print('  +0x%03x  ptr=%s  size=%s  CCountry=%s  其他=%s' % (a['off'], a['ptr'], a['size'], a['isCountry'], a['other']))
    for s in a['samples']:
        if 'name' in s:
            print('        [%3d] CCountry idx=%-4s name=%s' % (s['i'], s.get('idx'), s.get('name')))
        else:
            print('        [%3d] 非CCountry vt=%s' % (s['i'], s.get('vt')))
print('')
print('[4 字节 tag 模式搜索: 字母字母字母后跟 00]')
for b in r['aby']:
    print('  %s: %d 处' % (b['tag'], b['n']))
    for ad in b['addrs'][:8]:
        print('      %s' % ad)
try: frida.kill(pid)
except Exception: pass