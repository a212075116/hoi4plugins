# frida_country_tag2.py -- 在 CCountry 实例里找 3 字母国家 tag
#
# 思路: tag 是 3 个大写 ASCII 字母(HOI4 规则)。
# 先把每个实例的国家名读出来(已知在 +0x10 的 CString), 便于人工核对;
# 再在实例整块内存里找"恰好 3 个大写字母"的字节模式, 报告偏移。
# 这样 tag 的偏移是找出来的, 不是猜的。
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
        var dec = s;
        try { dec = decodeURIComponent(escape(s)); } catch (e) {}
        return dec;
    } catch (e) { return null; }
}
function isUpper(c) { return c >= 0x41 && c <= 0x5A; }
rpc.exports.run = function (n) {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), n);
    var out = [];
    for (var i = 0; i < inst.length; i++) {
        var o = inst[i];
        var name = readCString(o.add(0x10));
        var tags = [];
        // 在前 0x800 字节里找 3 连大写字母
        for (var off = 0; off + 3 <= 0x800; off++) {
            var a, b, c;
            try { a = o.add(off).readU8(); b = o.add(off+1).readU8(); c = o.add(off+2).readU8(); } catch (e) { break; }
            if (isUpper(a) && isUpper(b) && isUpper(c)) {
                // 前后不能再是大写字母, 否则是更长串的一部分
                var before = off > 0 ? o.add(off-1).readU8() : 0;
                var after = 0;
                try { after = o.add(off+3).readU8(); } catch (e) {}
                if (!isUpper(before) && !isUpper(after)) {
                    tags.push({off: off, tag: String.fromCharCode(a,b,c)});
                }
            }
        }
        out.push({obj: o.toString(), name: name, tags: tags});
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
res = sc.exports_sync.run(8)
for r in res:
    print('[%s]  name=%s' % (r['obj'], r['name']))
    for t in r['tags'][:14]:
        print('      +0x%03x  %s' % (t['off'], t['tag']))
try: frida.kill(pid)
except Exception: pass