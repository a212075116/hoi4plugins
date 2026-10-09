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
    try { var sz = Number(p.add(16).readU64()), cap = Number(p.add(24).readU64());
        if (sz === 0 || sz > 300 || cap < sz) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        return dp.readUtf8String(sz); } catch (e) { return null; }
}
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.probe = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), arr358: null, items: [], ccScan: []};
    var p358 = gs.add(0x358).readPointer();
    var n358 = u32(gs, 0x360);
    out.arr358 = {ptr: p358.toString(), n: n358};
    if (readable(p358, Math.min(n358, 40) * 32)) {
        for (var i = 0; i < Math.min(n358, 12); i++) {
            var e = p358.add(i * 32);
            var b = [];
            for (var o = 0; o < 32; o++) { var h = e.add(o).readU8().toString(16); if (h.length === 1) h = '0' + h; b.push(h); }
            var asc = '';
            for (var o2 = 0; o2 < 32; o2++) { var c = e.add(o2).readU8(); asc += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.'; }
            out.items.push({i: i, q0: e.readPointer().toString(), d8: u32(e, 8), d12: u32(e, 12), asc: asc, hex: b.join('')});
        }
    }
    // CCountry 前 3 个对象的完整 0x120 字节转储, 找 tag
    var carr = gs.add(0x310).readPointer();
    for (var ci = 1; ci <= 3; ci++) {
        var c = carr.add(ci * 8).readPointer();
        var lines = [];
        for (var off = 0; off < 0x120; off += 16) {
            var s = '';
            for (var o3 = 0; o3 < 16; o3++) { var cc = c.add(off + o3).readU8(); s += (cc >= 32 && cc < 127) ? String.fromCharCode(cc) : '.'; }
            var hx = '';
            for (var o4 = 0; o4 < 16; o4++) { var hh = c.add(off + o4).readU8().toString(16); if (hh.length === 1) hh = '0' + hh; hx += hh + ' '; }
            lines.push('+0x' + ('00' + off.toString(16)).slice(-3) + '  ' + hx + ' |' + s + '|');
        }
        out.ccScan.push({ci: ci, ptr: c.toString(), name: cstr(c.add(0x10)), lines: lines});
    }
    return out;
};