# frida_country_tag3.py -- 全对象范围搜 tag 字节
#
# 已知对照(来自 mod 的 localisation, 是权威事实):
#   格黑娜学园 -> GEH   百鬼夜行联合学院 -> HYA
# 所以在"格黑娜学园"这个实例里找 GEH 的字节, 找到的位置就是 tag 字段。
# 同时检查 3 种可能的存储形式: 裸 3 字节 / 4 字节带 NUL / 打包成整数(小端)。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);
function scanWhole(pat, cap) {
    var hits = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length && hits.length < cap; i++) {
        var r = ranges[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var found;
        try { found = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < found.length && hits.length < cap; j++) hits.push(found[j].address);
    }
    return hits;
}
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size > 512 || cap > 512 || cap < size || size === 0) return null;
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
function hexOf(o, off, n) {
    var s = '';
    for (var i = 0; i < n; i++) {
        try { s += ('0' + o.add(off+i).readU8().toString(16)).slice(-2) + ' '; } catch (e) { break; }
    }
    return s.trim();
}
rpc.exports.run = function () {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 200);
    var out = [];
    var want = { 'GEH': 1, 'HYA': 1 };
    for (var i = 0; i < inst.length; i++) {
        var o = inst[i];
        var nm = readCString(o.add(0x10));
        var found = [];
        // 整个对象范围(约 5904 字节)里找 3 连大写字母
        for (var off = 0; off + 3 <= 5904; off++) {
            var a, b, c;
            try { a = o.add(off).readU8(); b = o.add(off+1).readU8(); c = o.add(off+2).readU8(); } catch (e) { break; }
            if (a >= 0x41 && a <= 0x5A && b >= 0x41 && b <= 0x5A && c >= 0x41 && c <= 0x5A) {
                var before = off > 0 ? o.add(off-1).readU8() : 0;
                var after = 0; try { after = o.add(off+3).readU8(); } catch (e) {}
                var bU = before >= 0x41 && before <= 0x5A;
                var aU = after >= 0x41 && after <= 0x5A;
                if (!bU && !aU) {
                    var tg = String.fromCharCode(a,b,c);
                    found.push({off: off, tag: tg, ctx: hexOf(o, off, 8)});
                }
            }
        }
        out.push({obj: o.toString(), name: nm, hits: found});
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
time.sleep(3)
res = sc.exports_sync.run()
print('[共 %d 个实例]' % len(res))
for r in res:
    if r['name'] in ('格黑娜学园', '百鬼夜行联合学院') or (r['hits'] and len(r['hits']) <= 3):
        print('[%s] name=%s' % (r['obj'], r['name']))
        for h in r['hits']:
            print('      +0x%04x  %s   bytes: %s' % (h['off'], h['tag'], h['ctx']))
try: frida.kill(pid)
except Exception: pass