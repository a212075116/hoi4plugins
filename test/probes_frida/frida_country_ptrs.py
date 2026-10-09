# frida_country_ptrs.py -- 追 CCountry 里那 4 个堆指针, 看它们指向什么
#
# CCountry 实例 +0x70/+0x78/+0x80/+0x88 是堆对象指针, 一直没查过。
# tag 既不在对象内, 又必须能从国家推出, 那最可能的去处就是这几个被指向的对象。
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
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    var target = null;
    for (var i = 0; i < inst.length; i++) {
        if (readCString(inst[i].add(0x10)) === '格黑娜学园') { target = inst[i]; break; }
    }
    if (!target) return {err: 'not found'};
    var out = {obj: target.toString(), subs: []};
    var offs = [0x70, 0x78, 0x80, 0x88];
    for (var k = 0; k < offs.length; k++) {
        var p;
        try { p = target.add(offs[k]).readPointer(); } catch (e) { continue; }
        if (p.isNull()) continue;
        var rec = {off: offs[k], ptr: p.toString(), head: [], tag: null};
        // 该对象前 0x80 字节的 4 字节视图
        for (var q = 0; q < 0x40; q += 4) {
            var v;
            try { v = p.add(q).readU32(); } catch (e) { break; }
            rec.head.push(v);
        }
        // 在前 0x200 字节里找 tag 形态的 3 字符
        for (var r2 = 0; r2 + 3 <= 0x200; r2++) {
            var a, b, c;
            try { a = p.add(r2).readU8(); b = p.add(r2+1).readU8(); c = p.add(r2+2).readU8(); } catch (e) { break; }
            if (a >= 0x41 && a <= 0x5A && b >= 0x41 && b <= 0x5A && c >= 0x41 && c <= 0x5A) {
                var nx = 0; try { nx = p.add(r2+3).readU8(); } catch (e) {}
                if (!(nx >= 0x41 && nx <= 0x5A)) { rec.tag = String.fromCharCode(a,b,c) + ' @ +0x' + r2.toString(16); break; }
            }
        }
        out.subs.push(rec);
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
r = sc.exports_sync.run()
if r.get('err'): print('[!] ' + r['err'])
else:
    print('[格黑娜学园实例] %s' % r['obj'])
    for s in r['subs']:
        print('  +0x%02x -> %s   tag=%s' % (s['off'], s['ptr'], s['tag']))
        print('        前 32 字节(4B): ' + ' '.join('%08x' % v for v in s['head'][:8]))
try: frida.kill(pid)
except Exception: pass