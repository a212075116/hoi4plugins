# frida_lexer_tag.py -- 从全局词法表反查 tag
#
# 依据(IDA 反编译 sub_1424BC260, lexer.cpp):
#   qword_1435E1AE0 + 32 * index  ==> 词法表项, 每项 32 字节
#   index 超出 n18_0 会报 "not in the lookup table"
# 所以: 若 CCountry 里某个 4 字节字段是这种索引, 用它查表就能得到 tag 字符串。
# 做法: 先 dump 词法表若干项看布局, 再拿 CCountry 的候选字段去试。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var P_LEXER_INIT = base.add(0x35E1AB0);   // byte_1435E1AB0
var P_LEXER_TBL  = base.add(0x35E1AE0);   // qword_1435E1AE0
var P_LEXER_CNT  = base.add(0x35E1AD8);   // n18_0 附近
var VT_COUNTRY   = base.add(0x27E7360);
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
    var out = {};
    out.initFlag = P_LEXER_INIT.readU8();
    var tbl = P_LEXER_TBL.readPointer();
    out.tbl = tbl.toString();
    var cnt = P_LEXER_CNT.readPointer();   // 可能直接是整数, 先当指针试; 失败下面补
    out.cntRaw = P_LEXER_CNT.readU64().toString();
    // dump 前 12 项 (每项 32 字节)
    out.entries = [];
    for (var i = 0; i < 12; i++) {
        var e = tbl.add(i * 32);
        var q = [];
        var s = null;
        for (var k = 0; k < 4; k++) {
            var v;
            try { v = e.add(k * 8).readU64().toString(); } catch (err) { v = '?'; }
            q.push(v);
        }
        try { s = e.readUtf8String(24); } catch (err) {}
        // 若第 0 个 qword 像指针, 再试读字符串
        if (!s) {
            try {
                var p0 = e.readPointer();
                if (!p0.isNull()) s = p0.readUtf8String(24);
            } catch (err) {}
        }
        out.entries.push({idx: i, q: q, s: s});
    }
    // CCountry 实例, 用其候选 4 字节字段查表
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    out.nCountry = inst.length;
    out.tryFields = [];
    for (var n = 0; n < Math.min(inst.length, 4); n++) {
        var o = inst[n];
        var nm = readCString(o.add(0x10));
        var row = {name: nm, u32: []};
        for (var off = 0; off < 0x60; off += 4) {
            var val;
            try { val = o.add(off).readU32(); } catch (e) { break; }
            // 只关心像"词法表索引"的小整数
            if (val > 0 && val < 200000) {
                var s2 = null;
                try {
                    var e2 = tbl.add(val * 32);
                    var p2 = e2.readPointer();
                    if (!p2.isNull()) s2 = p2.readUtf8String(16);
                    if (!s2) s2 = e2.readUtf8String(16);
                } catch (err) {}
                if (s2 && /^[A-Za-z0-9_]{2,12}$/.test(s2)) row.u32.push({off: off, idx: val, str: s2});
            }
        }
        out.tryFields.push(row);
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
print('[lexer init flag] %s' % r['initFlag'])
print('[lexer table] %s   cntRaw=%s' % (r['tbl'], r['cntRaw']))
print('[前 12 项]')
for e in r['entries']:
    print('    #%-3d  q=%s  s=%s' % (e['idx'], ' | '.join(x[:14] for x in e['q']), e['s']))
print('[CCountry 实例数] %s' % r['nCountry'])
for row in r['tryFields']:
    print('[%s]' % row['name'])
    for u in row['u32'][:12]:
        print('    +0x%02x  idx=%-8d -> "%s"' % (u['off'], u['idx'], u['str']))
try: frida.kill(pid)
except Exception: pass