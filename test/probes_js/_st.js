var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_FLEET = base.add(0x2962A18);
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function readable(p, n) {
    var rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
rpc.exports.st = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull()) return {ok: false};
        var cd = null, cn = u32(gs, 0x6A8 + 0x1C);
        try { cd = gs.add(0x6A8 + 0x10).readPointer(); } catch (e) {}
        var live = -1;
        if (cd && cn > 0 && cn < 20000) {
            live = 0;
            for (var i = 0; i < cn; i++) {
                try { var o = cd.add(i * 8).readPointer(); if (!o.isNull() && readable(o, 8)) { if (o.readPointer().equals(base.add(0x297EA60))) live++; } } catch (e2) {}
            }
        }
        var ftot = 0, fct = 0;
        var carr = gs.add(0x310).readPointer();
        var cnum = u32(gs, 0x318);
        for (var ci = 0; ci < cnum; ci++) {
            try {
                var c = carr.add(ci * 8).readPointer();
                if (c.isNull() || !readable(c, 0x300)) continue;
                var n = u32(c, 0x284);
                if (n && n > 0 && n < 10000) { ftot += n; fct++; }
            } catch (e3) {}
        }
        return {ok: true, chars: cn, charLive: live, countries: cnum, fleetCountries: fct, fleets: ftot};
    } catch (e) { return {ok: false, why: '' + e}; }
};