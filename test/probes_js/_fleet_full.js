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
function readCSHex(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz > 400 || cap < sz || cap > 400) return null;
        if (sz === 0) return '';
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) { var h = dp.add(i).readU8().toString(16); if (h.length === 1) h = '0' + h; s += h; }
        return s;
    } catch (e) { return null; }
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, gs: gs.toString(), countries: u32(gs, 0x318), provinces: u32(gs, 0x2B8)}; } catch (e) { return {ok:false}; } };
rpc.exports.fleetCount = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tot = 0;
        for (var ci = 0; ci < cnum; ci++) {
            try { var c = carr.add(ci * 8).readPointer(); if (c.isNull() || !readable(c, 0x300)) continue;
                var n = u32(c, 0x284); if (n && n > 0 && n < 10000) tot += n; } catch (e) {}
        }
        return tot;
    } catch (e) { return -1; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x318);
    var out = {base: base.toString(), gs: gs.toString(), provinces: u32(gs, 0x2B8), countries: cnum, rows: [], totalFleets: 0};
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var arr = null, num = null;
        try { arr = c.add(0x278).readPointer(); } catch (e) {}
        try { num = u32(c, 0x284); } catch (e) {}
        var rec = {ci: ci, c: c.toString(), arr: arr ? arr.toString() : null, num: num, fleets: []};
        if (num !== null && num > 0 && num < 10000 && arr && !arr.isNull() && readable(arr, num * 8)) {
            for (var fi = 0; fi < num; fi++) {
                var f; try { f = arr.add(fi * 8).readPointer(); } catch (e) { rec.fleets.push({fi: fi, err: 'slot'}); continue; }
                if (f.isNull()) { rec.fleets.push({fi: fi, null: true}); continue; }
                if (!readable(f, 0x130)) { rec.fleets.push({fi: fi, ptr: f.toString(), unreadable: true}); continue; }
                var vt = null; try { vt = f.readPointer(); } catch (e) {}
                rec.fleets.push({fi: fi, ptr: f.toString(), vtOk: (vt && vt.equals(VT_FLEET)),
                                 tag: u32(f, 8), refid: u32(f, 12), f18: (function(){ try { return f.add(0x18).readPointer().toString(); } catch(e){ return null; } })(),
                                 hex: readCSHex(f.add(0xE0)), hex48: readCSHex(f.add(0x48)), hexB8: readCSHex(f.add(0xB8))});
            }
            out.totalFleets += num;
        }
        out.rows.push(rec);
    }
    return out;
};