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
function tagStr(t) {
    if (!t) return null;
    var s = '';
    for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); }
    return s;
}
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.go = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), first: [], n: null, cc: []};
    var p = gs.add(0x358).readPointer(); var n = u32(gs, 0x360);
    out.n = n; out.ptr = p.toString();
    for (var i = 0; i < Math.min(n, 10); i++) {
        var t = u32(p, i * 32);
        out.first.push({i: i, tag: tagStr(t), raw: t, s16: u32(p, i * 32 + 16), s24: u32(p, i * 32 + 24)});
    }
    // 前 8 个 CCountry 与 tag 表同索引对照
    var carr = gs.add(0x310).readPointer();
    for (var ci = 0; ci < 10; ci++) {
        var c = carr.add(ci * 8).readPointer();
        var nm = null;
        try { var sz = Number(c.add(0x10).readU64()), cap = Number(c.add(0x18).readU64());
              var dp = (cap > 15) ? c.add(0x10).readPointer() : c.add(0x10);
              if (sz > 0 && sz < 200) nm = dp.readUtf8String(sz); } catch (e) {}
        var t2 = tagStr(u32(p, ci * 32));
        out.cc.push({ci: ci, idx: u32(c, 8), name: nm, tagAtSameIdx: t2});
    }
    return out;
};