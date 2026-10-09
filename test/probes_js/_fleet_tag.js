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
rpc.exports.dump = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x318);
    var out = {gs: gs.toString(), countries: cnum, rows: [], tot: 0, nl: 0};
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var n = u32(c, 0x284);
        var ar = null; try { ar = c.add(0x278).readPointer(); } catch (e) {}
        if (n && n > 0 && n < 10000) {
            out.tot += n;
            if (out.rows.length < 60) out.rows.push({ci: ci, c: c.toString(), arr: ar ? ar.toString() : null, num: n});
        }
        if (ar && !ar.isNull()) out.nl++;
    }
    return out;
};
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };