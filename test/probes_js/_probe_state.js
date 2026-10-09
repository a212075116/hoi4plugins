var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_FLEET = base.add(0x2962A18);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer().toString(); } catch (e) { return null; } }
rpc.exports.status = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull() || !readable(gs, 0x800)) return {ok: false, why: 'GS'};
        return {ok: true, provinces: u32(gs, 0x2B8), countries: u32(gs, 0x318), chars: u32(gs, 0x6A8 + 0x1C)};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.dump = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(),
               provinces: u32(gs, 0x2B8),
               states: u32(gs, 0x2C8 + 8),
               countries: u32(gs, 0x318),
               charsNum: u32(gs, 0x6A8 + 0x1C),
               charsData: u64(gs, 0x6A8 + 0x10),
               charsLive: 0, rows: []};
    try {
        var cd = gs.add(0x6A8 + 0x10).readPointer();
        var cn = u32(gs, 0x6A8 + 0x1C);
        var live = 0;
        for (var i = 0; i < cn && i < 3000; i++) {
            var o = cd.add(i * 8).readPointer();
            if (!o.isNull() && readable(o, 0x130)) { var vt = o.readPointer(); if (vt.equals(base.add(0x297EA60))) live++; }
        }
        out.charsLive = live;
    } catch (e) { out.charsLive = 'err:' + e; }
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x318);
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var n = u32(c, 0x284); var ar = null; try { ar = c.add(0x278).readPointer(); } catch (e) {}
        if (n) out.rows.push({ci: ci, c: c.toString(), num: n, arr: ar ? ar.toString() : null});
    }
    return out;
};
rpc.exports.scanVt = function () {
    var wr = Process.enumerateRanges('rw-');
    var pat = VT_FLEET.toMatchPattern();
    var raw = 0, strong = 0;
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var hits; try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        raw += hits.length;
    }
    return {raw: raw, strong: strong};
};