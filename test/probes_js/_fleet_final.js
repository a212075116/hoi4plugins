var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_FLEET = base.add(0x2962A18);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) { var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true; }
    return false;
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function cs(p) {
    try { var sz = Number(p.add(16).readU64()), cap = Number(p.add(24).readU64());
        if (sz === 0) return '';
        if (sz > 300 || cap < sz) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        return dp.readUtf8String(sz); } catch (e) { return null; }
}
function tagOf(t) { if (!t) return null; var s = '';
    for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318), provinces: u32(gs, 0x2B8)}; } catch (e) { return {ok:false}; } };
rpc.exports.fleetCount = function () {
    try { var gs = GS_GLOBAL.readPointer();
        var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tot = 0;
        for (var ci = 0; ci < cnum; ci++) { try { var c = carr.add(ci * 8).readPointer();
            if (c.isNull() || !readable(c, 0x300)) continue; var n = u32(c, 0x284);
            if (n && n > 0 && n < 10000) tot += n; } catch (e) {} }
        return tot; } catch (e) { return -1; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318);
    var tp = gs.add(0x358).readPointer(); var tn = u32(gs, 0x360);
    var out = {base: base.toString(), gs: gs.toString(), provinces: u32(gs, 0x2B8), countries: cnum,
               tagTablePtr: tp.toString(), tagTableN: tn, rows: [], total: 0, vtok: 0, objs: []};
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var arr = null, num = null;
        try { arr = c.add(0x278).readPointer(); } catch (e) {}
        try { num = u32(c, 0x284); } catch (e) {}
        var ctag = tagOf(u32(tp, ci * 32));
        var cname = cs(c.add(0x10)), cshort = cs(c.add(0x30));
        var rec = {ci: ci, c: c.toString(), ctag: ctag, cname: cname, cshort: cshort, arr: arr ? arr.toString() : null, num: num, fleets: []};
        if (num !== null && num > 0 && num < 10000 && arr && !arr.isNull() && readable(arr, num * 8)) {
            for (var fi = 0; fi < num; fi++) {
                var f; try { f = arr.add(fi * 8).readPointer(); } catch (e) { rec.fleets.push({fi: fi, err: 'slot'}); continue; }
                if (f.isNull()) { rec.fleets.push({fi: fi, null: true}); continue; }
                if (!readable(f, 0x130)) { rec.fleets.push({fi: fi, ptr: f.toString(), unreadable: true}); continue; }
                var vt = null; try { vt = f.readPointer(); } catch (e) {}
                var fvt = (vt && vt.equals(VT_FLEET));
                var country = null, cn2 = null;
                try { country = f.add(0xA8).readPointer(); } catch (e) {}
                var rec2 = {fi: fi, ptr: f.toString(), vtOk: fvt, refid: u32(f, 12), d8: u32(f, 8),
                            name: cs(f.add(0xE0)), nameLen: (function(){ try { return Number(f.add(0xF0).readU64()); } catch(e){ return null; } })(),
                            nameCap: (function(){ try { return Number(f.add(0xF8).readU64()); } catch(e){ return null; } })(),
                            c48: cs(f.add(0x48)), cB8: cs(f.add(0xB8)),
                            countryPtr: country ? country.toString() : null};
                if (fvt) out.vtok++;
                out.total++;
                out.objs.push({ctag: ctag, ci: ci, ptr: f.toString(), refid: rec2.refid, name: rec2.name});
                rec.fleets.push(rec2);
            }
        }
        out.rows.push(rec);
    }
    return out;
};