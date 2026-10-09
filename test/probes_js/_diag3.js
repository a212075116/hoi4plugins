var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT = {
  CShip_a: base.add(0x2957F28),
  CShip_b: base.add(0x2957F90),
  CTaskForce_a: base.add(0x2962F70),
  CFleet_a: base.add(0x2962A18),
  CFleet_b: base.add(0x2962A70)
};
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318), chars: u32(gs, 0x6A8+0x1C)}; } catch (e) { return {ok:false}; } };
rpc.exports.scan = function () {
    var wr = Process.enumerateRanges('rw-');
    var out = {};
    for (var k in VT) {
        var pat = VT[k].toMatchPattern();
        var n = 0, samp = [];
        for (var i = 0; i < wr.length; i++) {
            var r = wr[i];
            if (r.size > 256 * 1024 * 1024) continue;
            try {
                var h = Memory.scanSync(r.base, r.size, pat);
                n += h.length;
                for (var j = 0; j < h.length && samp.length < 6; j++) samp.push(h[j].address.toString());
            } catch (e) {}
        }
        out[k] = {n: n, samples: samp};
    }
    return out;
};