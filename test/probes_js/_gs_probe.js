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
function cstr(p) {
    try {
        var sz = Number(p.add(16).readU64()), cap = Number(p.add(24).readU64());
        if (sz === 0 || sz > 300 || cap < sz) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        return dp.readUtf8String(sz);
    } catch (e) { return null; }
}
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.probe = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), candidates: [], cc0x10: null};
    // 候选: CGameState 若干偏移处的 {ptr, count}
    var offs = [0x2B0, 0x2C8, 0x310, 0x328, 0x340, 0x358, 0x370, 0x388, 0x3A0];
    for (var i = 0; i < offs.length; i++) {
        var o = offs[i];
        var p = null, n = null;
        try { p = gs.add(o).readPointer(); } catch (e) {}
        try { n = u32(gs, o + 8); } catch (e) {}
        var rec = {off: o, ptr: p ? p.toString() : null, n: n, sample: []};
        if (p && !p.isNull() && n && n > 0 && n < 5000 && readable(p, Math.min(n, 20) * 8)) {
            for (var j = 0; j < Math.min(n, 6); j++) {
                var e2 = null; try { e2 = p.add(j * 8).readPointer(); } catch (e) {}
                rec.sample.push(e2 ? e2.toString() : null);
            }
            rec.cstrs = [];
            for (var j2 = 0; j2 < Math.min(n, 6); j2++) {
                var e3 = null; try { e3 = p.add(j2 * 8).readPointer(); } catch (e) {}
                if (e3 && !e3.isNull() && readable(e3, 32)) rec.cstrs.push(cstr(e3));
            }
        }
        out.candidates.push(rec);
    }
    // CCountry 的 +0x10 里到底是什么
    var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318);
    out.ccs = [];
    for (var ci = 0; ci < Math.min(cnum, 6); ci++) {
        var c = carr.add(ci * 8).readPointer();
        out.ccs.push({ci: ci, p: c.toString(), idx: u32(c, 8),
                      q10: c.add(0x10).readPointer().toString(),
                      s10: cstr(c.add(0x10)),
                      q30: cstr(c.add(0x30)), q50: cstr(c.add(0x50))});
    }
    return out;
};