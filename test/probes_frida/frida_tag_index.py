# frida_tag_index.py -- 反查法定位 tag 字段
#
# 前几轮的错误做法: 猜 CCountry 里哪个偏移是 tag, 然后验证。
# 正确做法: 先去词法表里找到 tag 字符串(如 GEH)对应的下标, 再拿这个下标值去对象里搜。
# 这样 tag 字段是被搜出来的。
#
# 词法表(IDA 反编译 sub_1424BC260 得出):
#   qword_1435E1AE0 + 32 * index, 每项 32 字节 MSVC std::string
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var P_TBL = base.add(0x35E1AE0);
var P_INIT = base.add(0x35E1AB0);
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
// 按 MSVC std::string 规则读表项
function entryStr(e) {
    try {
        var size = e.add(16).readU64().toNumber();
        var cap  = e.add(24).readU64().toNumber();
        if (size === 0 || size > 64 || cap > 64 || cap < size) return null;
        var dp = (cap > 15) ? e.readPointer() : e;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dp.add(i).readU8());
        return s;
    } catch (err) { return null; }
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
rpc.exports.run = function (maxScan) {
    var out = {init: P_INIT.readU8(), found: {}, nLex: 0};
    var tbl = P_TBL.readPointer();
    out.tbl = tbl.toString();
    // 顺序扫描词法表, 记录三个 tag 的下标
    var want = {'ABY':1, 'GEH':1, 'HYA':1, 'PMC':1};
    var idx = 0;
    var bad = 0;
    while (idx < maxScan) {
        var e = tbl.add(idx * 32);
        var s = entryStr(e);
        if (s === null) {
            bad++;
            if (bad > 200) break;   // 连续读不到就当表结束
        } else {
            bad = 0;
            if (want[s]) out.found[s] = idx;
        }
        idx++;
    }
    out.nLex = idx;
    // 拿找到的下标去 CCountry 里搜
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    out.nCountry = inst.length;
    out.hits = [];
    var tags = Object.keys(out.found);
    for (var k = 0; k < tags.length; k++) {
        var tag = tags[k];
        var ix = out.found[tag];
        var pat = ix.toString(16);
        var bytes = [];
        var v = ix;
        for (var b = 0; b < 4; b++) { bytes.push(v & 0xff); v = Math.floor(v / 256); }
        var hex = bytes.map(function (x) { return ('0' + x.toString(16)).slice(-2); }).join(' ');
        for (var n = 0; n < inst.length; n++) {
            var o = inst[n];
            var nm = readCString(o.add(0x10));
            // 在该对象 5904 字节里找这个 4 字节值(每 4 字节对齐查一次)
            for (var off = 0; off + 4 <= 5904; off += 4) {
                var val;
                try { val = o.add(off).readU32(); } catch (err) { break; }
                if (val === ix) out.hits.push({tag: tag, idx: ix, name: nm, off: off});
            }
        }
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
r = sc.exports_sync.run(400000)
print('[lexer init] %s   [表基址] %s   [扫描项数] %d' % (r['init'], r['tbl'], r['nLex']))
print('[词法表里找到的 tag 下标]')
for t, i in r['found'].items():
    print('    %-5s -> index %d' % (t, i))
print('[CCountry 实例数] %s' % r['nCountry'])
print('[对象内命中该下标的偏移] %d 处' % len(r['hits']))
seen = set()
for h in r['hits'][:40]:
    key = (h['tag'], h['off'])
    if key in seen: continue
    seen.add(key)
    print('    %-5s idx=%-8d +0x%04x   对象=%s' % (h['tag'], h['idx'], h['off'], h['name']))
try: frida.kill(pid)
except Exception: pass