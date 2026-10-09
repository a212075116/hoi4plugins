var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
rpc.exports.info = function () {
  var rs = Process.enumerateRanges('rw-'); var tot = 0, big = 0;
  for (var i = 0; i < rs.length; i++) { tot += rs[i].size; if (rs[i].size > 64 * 1024 * 1024) big++; }
  return { n: rs.length, totalMB: Math.round(tot / 1048576), big: big };
};
rpc.exports.scanAll = function () {
  var pats = [ { tag: 'CShip_a', rva: 0x2957F28 }, { tag: 'CShip_b', rva: 0x2957F90 },
               { tag: 'CTaskForce_a', rva: 0x2962F70 }, { tag: 'CFleet_a', rva: 0x2962A18 } ];
  var rs = Process.enumerateRanges('rw-');
  var out = {}; var t0 = Date.now();
  for (var p = 0; p < pats.length; p++) { out[pats[p].tag] = { n: 0, samples: [] }; }
  for (var i = 0; i < rs.length; i++) {
    var r = rs[i];
    if (r.size > 256 * 1024 * 1024) continue;
    for (var p = 0; p < pats.length; p++) {
      var pat = base.add(pats[p].rva).toMatchPattern();
      try { var h = Memory.scanSync(r.base, r.size, pat);
        out[pats[p].tag].n += h.length;
        for (var j = 0; j < h.length && out[pats[p].tag].samples.length < 10; j++) out[pats[p].tag].samples.push(h[j].address.toString());
      } catch (e) {}
    }
  }
  out._ms = Date.now() - t0; out._ranges = rs.length;
  return out;
};
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  var chi = null;
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') { chi = { fleets: u32(c, 0x284), idx: ci }; break; } }
  return { ok: true, countries: cnum, chi: chi }; } catch (e) { return { ok: false, err: String(e) }; } };
