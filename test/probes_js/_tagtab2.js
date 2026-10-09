var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) { var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true; }
    return false;
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.go = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), t358: [], t328: [], gsDump: []};
    function dumpArr(off, label, maxItems, itemSize) {
        var p = null, n = null;
        try { p = gs.add(off).readPointer(); } catch (e) {}
        try { n = u32(gs, off + 8); } catch (e) {}
        var r = {off: off, label: label, ptr: p ? p.toString() : null, n: n, items: []};
        if (p && !p.isNull() && n && n > 0 && n < 100000 && readable(p, Math.min(n, maxItems) * itemSize)) {
            for (var i = 0; i < Math.min(n, maxItems); i++) {
                var e = p.add(i * itemSize);
                var asc = '';
                for (var o = 0; o < itemSize; o++) { var ch = e.add(o).readU8(); asc += (ch >= 32 && ch < 127) ? String.fromCharCode(ch) : '.'; }
                var dw = []; for (var o2 = 0; o2 < itemSize; o2 += 4) dw.push(u32(e, o2));
                r.items.push({i: i, asc: asc, dw: dw});
            }
        }
        return r;
    }
    out.t358 = dumpArr(0x358, 'CGameState+0x358', 24, 32);
    out.t328 = dumpArr(0x328, 'CGameState+0x328', 16, 16);
    out.t340 = dumpArr(0x340, 'CGameState+0x340', 12, 32);
    out.t370 = dumpArr(0x370, 'CGameState+0x370', 12, 8);
    return out;
};