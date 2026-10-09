# frida_country_diff.py -- diff 两个已知 tag 的国家实例, 定位 tag 字段
#
# 已知事实(mod localisation 提供, 权威): 格黑娜学园=GEH, 百鬼夜行联合学院=HYA
# 这两个 tag 不同, 所以 tag 字段的取值必然不同。
# 做法: 逐 4 字节比对两个实例, 列出所有"值小且不同"的位置 —— tag 必在其中。
# 另外把 GEH 的两种常见打包形式算出来对照。
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
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 200);
    var geh = null, hya = null;
    for (var i = 0; i < inst.length; i++) {
        var nm = readCString(inst[i].add(0x10));
        if (nm === '格黑娜学园') geh = inst[i];
        if (nm === '百鬼夜行联合学院') hya = inst[i];
    }
    if (!geh || !hya) return {err: 'not found'};
    var diffs = [];
    for (var off = 0; off + 8 <= 5904; off += 4) {
        var a, b;
        try { a = geh.add(off).readU32(); b = hya.add(off).readU32(); } catch (e) { break; }
        if (a !== b) {
            // 只关心"像索引或小编码"的值
            if (a < 0x10000 && b < 0x10000) {
                diffs.push({off: off, geh: a, hya: b});
            }
        }
    }
    return {err: null, geh: geh.toString(), hya: hya.toString(), n: diffs.length, diffs: diffs};
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

# GEH / HYA 的几种可能打包方式, 用来对照
def pack5(t):
    v = 0
    for i, c in enumerate(t):
        v |= ((ord(c) - 64) & 0x1F) << (5 * i)
    return v
print('[参照] GEH 5bit小端=%#x  HYA 5bit小端=%#x' % (pack5('GEH'), pack5('HYA')))
print('[参照] GEH 5bit大端=%#x  HYA 5bit大端=%#x' % (int.from_bytes(bytes([(ord(c)-64) for c in 'GEH']), 'big'),
      int.from_bytes(bytes([(ord(c)-64) for c in 'HYA']), 'big')))

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(3)
r = sc.exports_sync.run()
if r.get('err'):
    print('[!] ' + str(r['err']))
else:
    print('[GEH 实例] %s' % r['geh'])
    print('[HYA 实例] %s' % r['hya'])
    print('[小值差异] %d 处' % r['n'])
    for d in r['diffs'][:40]:
        print('    +0x%04x   GEH=%#010x (%d)   HYA=%#010x (%d)' % (d['off'], d['geh'], d['geh'], d['hya'], d['hya']))
try: frida.kill(pid)
except Exception: pass