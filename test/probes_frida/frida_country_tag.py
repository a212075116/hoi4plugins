# frida_country_tag.py -- 从 CCountry 实例里解出国家 tag
#
# 依据: MSVC std::string 是 32 字节 { 16 字节数据区, size_t size, size_t capacity }。
# 内联(SSO)时数据区直接放字节; 超过 15 字节则数据区放堆指针。
# 所以对实例里每个可能的 CString, 先看 size/capacity 是否自洽, 再按规则取字符串。
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
// 按 MSVC std::string 规则读一个 CString
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size > 512 || cap > 512 || cap < size) return null;
        var dataP = p;
        if (cap > 15) dataP = p.readPointer();
        var b = new Uint8Array(size);
        for (var i = 0; i < size; i++) b[i] = dataP.add(i).readU8();
        var s = '';
        for (var k = 0; k < b.length; k++) s += String.fromCharCode(b[k]);
        var dec = '';
        try { dec = decodeURIComponent(escape(s)); } catch (e) { dec = s; }
        return {size: size, cap: cap, raw: dec};
    } catch (e) { return null; }
}
rpc.exports.run = function (n) {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), n);
    var out = [];
    for (var i = 0; i < inst.length; i++) {
        var o = inst[i];
        var found = [];
        for (var off = 8; off + 32 <= 0x120; off += 8) {
            var cs = readCString(o.add(off));
            if (cs && cs.size > 0) found.push({off: off, size: cs.size, cap: cs.cap, raw: cs.raw});
        }
        out.push({obj: o.toString(), fields: found});
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
res = sc.exports_sync.run(6)
for r in res:
    print('[%s]' % r['obj'])
    for f in r['fields']:
        print('    +0x%03x  size=%-3d cap=%-3d  "%s"' % (f['off'], f['size'], f['cap'], f['raw']))
try: frida.kill(pid)
except Exception: pass