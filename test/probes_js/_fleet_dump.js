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
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, gs: gs.toString(), countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.dumpOne = function (wantTag) {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318);
    var out = {found: null, hex: null, ptrs: [], country: null, countryHex: null, tagStr: null, tagIdx: null};
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var n = u32(c, 0x284); if (!n || n < 1 || n > 10000) continue;
        var arr = c.add(0x278).readPointer();
        var f = arr.readPointer();
        if (f.isNull() || !readable(f, 0x130)) continue;
        var vt = f.readPointer(); if (!vt.equals(VT_FLEET)) continue;
        // 记录这个 CCountry 的关键字段以推断 tag
        out.country = c.toString();
        out.countryIdx = ci;
        // CCountry 名字 CString @ +0x10
        var cs = ''; try {
            var sz = Number(c.add(0x10).readU64()); var cap = Number(c.add(0x18).readU64());
            var dp = (cap > 15) ? c.add(0x10).readPointer() : c.add(0x10);
            if (sz > 0 && sz < 200 && readable(dp, sz)) cs = dp.readUtf8String(sz);
        } catch (e) {}
        out.countryName = cs;
        out.fleetPtr = f.toString();
        var bytes = [];
        for (var o = 0; o < 0x130; o++) { var h = f.add(o).readU8().toString(16); if (h.length === 1) h = '0' + h; bytes.push(h); }
        out.hex = bytes.join('');
        // 同时记录该 CCountry 的 +0x08 值(索引) 以对照
        out.countryIdxField = u32(c, 0x08);
        return out;
    }
    return out;
};
rpc.exports.tagScan = function () {
    // 统计所有 CFleet 的 +0x08 低4字节 / +0x0C 高4字节
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318);
    var lows = {}, highs = {}, pairs = [];
    for (var ci = 0; ci < cnum; ci++) {
        var c; try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var n = u32(c, 0x284); if (!n || n < 1 || n > 10000) continue;
        var arr = c.add(0x278).readPointer();
        for (var fi = 0; fi < n; fi++) {
            var f; try { f = arr.add(fi * 8).readPointer(); } catch (e) { continue; }
            if (f.isNull() || !readable(f, 0x130)) continue;
            var vt = f.readPointer(); if (!vt.equals(VT_FLEET)) continue;
            var lo = u32(f, 8), hi = u32(f, 12);
            lows[lo] = (lows[lo] || 0) + 1; highs[hi] = (highs[hi] || 0) + 1;
            pairs.push([ci, lo, hi, u32(f, 0xA8), u32(f, 0xB0), f.add(0xA8).readPointer().toString()]);
        }
    }
    return {lows: lows, highsN: Object.keys(highs).length, sample: pairs.slice(0, 20), n: pairs.length};
};