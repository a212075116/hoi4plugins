var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT = {
  CCharacter: base.add(0x297EA60),
  CFleet: base.add(0x2962A18),
  CCountry: base.add(0x27E7360),
  CProvince: base.add(0x2971B18),
  CState: base.add(0x2936CC0)
};
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return {ok:false}; return {ok:true, countries: u32(gs, 0x318)}; } catch (e) { return {ok:false}; } };
rpc.exports.scan = function () {
    var wr = Process.enumerateRanges('rw-');
    var out = {};
    for (var k in VT) {
        var pat = VT[k].toMatchPattern();
        var n = 0;
        for (var i = 0; i < wr.length; i++) {
            var r = wr[i];
            if (r.size > 256 * 1024 * 1024) continue;
            try { n += Memory.scanSync(r.base, r.size, pat).length; } catch (e) {}
        }
        out[k] = n;
    }
    return out;
};