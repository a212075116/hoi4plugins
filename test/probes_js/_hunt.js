var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_FLEET = base.add(0x2962A18);
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.status = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull()) return {ok: false, why: 'GS'};
        return {ok: true, chars: u32(gs, 0x6A8 + 0x1C), countries: u32(gs, 0x318)};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.hunt = function () {
    var gs = GS_GLOBAL.readPointer();
    var res = {gs: gs.toString(), chars: u32(gs, 0x6A8 + 0x1C),
               charsData: (function(){ try { return gs.add(0x6A8+0x10).readPointer().toString(); } catch(e){ return null; } })(),
               needles: {}, vtscan: null};
    var needles = ['Di 1 Jiandui', 'Ninghai', 'Hairong', 'Zhaohe', 'FLEET_NAME_NOT_SET'].
        map(function (s) { return {s: s, hex: s.split('').map(function(c){var h=c.charCodeAt(0).toString(16); return h.length===1?'0'+h:h;}).join('')}; });
    var wr = Process.enumerateRanges('rw-');
    for (var k = 0; k < needles.length; k++) {
        var nd = needles[k];
        var hits = [];
        for (var i = 0; i < wr.length; i++) {
            var r = wr[i];
            if (r.size > 256 * 1024 * 1024) continue;
            try {
                var h = Memory.scanSync(r.base, r.size, nd.hex);
                for (var j = 0; j < h.length; j++) if (hits.length < 40) hits.push(h[j].address.toString());
            } catch (e) {}
        }
        res.needles[nd.s] = {count: hits.length, addrs: hits.slice(0, 12)};
    }
    // CFleet 虚表扫描 + 用基址区间分类
    var pat = VT_FLEET.toMatchPattern();
    var raw = 0, inExe = 0, outExe = 0, samples = [];
    for (var i = 0; i < wr.length; i++) {
        var r2 = wr[i];
        if (r2.size > 256 * 1024 * 1024) continue;
        try {
            var h2 = Memory.scanSync(r2.base, r2.size, pat);
            raw += h2.length;
            for (var j2 = 0; j2 < h2.length; j2++) {
                var a = h2[j2].address;
                if (samples.length < 10) samples.push(a.toString());
            }
        } catch (e2) {}
    }
    res.vtscan = {raw: raw, samples: samples};
    // CCharacter 管理器作为正对照
    try {
        var cd = gs.add(0x6A8 + 0x10).readPointer();
        var cn = u32(gs, 0x6A8 + 0x1C);
        var live = 0, ok0 = 0;
        for (var i3 = 0; i3 < cn && i3 < 5000; i3++) {
            var o = cd.add(i3 * 8).readPointer();
            if (o.isNull()) continue; ok0++;
            try { if (o.readPointer().equals(base.add(0x297EA60))) live++; } catch (e3) {}
        }
        res.charCheck = {num: cn, dataPtr: cd.toString(), nonNull: ok0, live: live};
    } catch (e4) { res.charCheck = {err: '' + e4}; }
    return res;
};