var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = {
  0x27E7360: 'CCountry', 0x2962A18: 'CFleet_a', 0x2962A70: 'CFleet_b',
  0x2957F28: 'CShip_a', 0x2957F90: 'CShip_b',
  0x2962F70: 'CTaskForce_a', 0x2963150: 'CTaskForce_b', 0x29631C0: 'CTaskForce_c', 0x2963208: 'CTaskForce_d',
  0x295A2B0: 'CArmy_a', 0x295A490: 'CArmy_b', 0x295A500: 'CArmy_c', 0x295A548: 'CArmy_d',
  0x29530D8: 'CUnit_a', 0x29532B0: 'CUnit_b', 0x2953320: 'CUnit_c',
  0x2971B18: 'CProvince_a', 0x2971B68: 'CProvince_b', 0x2936CC0: 'CState_a', 0x2936D10: 'CState_b'
};
var VTMAP = {};
for (var k in VTN) VTMAP[base.add(parseInt(k)).toString()] = VTN[k];
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || null; } catch (e) { return null; } }
function chiC(gs) { var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; } return null; }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); if (!cc) return { ok: true, chi: null };
  return { ok: true, chi: { fleets: u32(cc.c, 0x284), armies: u32(cc.c, 0x29C), idx: cc.idx, ptr: cc.c.toString() } }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.dumpArmies = function (n) {
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); if (!cc) return { ok: false, err: 'no CHI' };
  var c = cc.c;
  var ad = u64(c, 0x290); var an = u32(c, 0x29C);
  var out = { ok: true, armyData: ad ? ad.toString() : null, armyCount: an, armies: [] };
  var lim = (n && n > 0) ? Math.min(n, an) : an;
  for (var i = 0; i < lim; i++) {
    var a = ad.add(8 * i).readPointer();
    var rec = { i: i, ptr: a.toString(), vt: vtName(a), hex: hex(a, 0x400), cand: [], names: [] };
    for (var off = 0; off <= 0x3F0; off += 8) {
      if (off + 0x20 <= 0x400) { var nm = cstr(a.add(off)); if (nm && nm.length >= 2 && nm.length <= 80) rec.names.push({ off: off, name: nm }); }
    }
    for (var off2 = 0; off2 <= 0x3F0; off2 += 8) {
      var data = u64(a, off2); if (!data || data.isNull()) continue;
      var cnt = u32(a, off2 + 0x0C);
      if (cnt === null || cnt <= 0 || cnt > 5000) continue;
      var hits = [];
      for (var k = 0; k < Math.min(cnt, 6); k++) {
        try { var e = data.add(8 * k).readPointer(); if (e.isNull()) continue; var nm2 = vtName(e);
          if (nm2) hits.push({ i: k, ptr: e.toString(), vt: nm2 }); } catch (e2) {}
      }
      if (hits.length) rec.cand.push({ off: off2, data: data.toString(), count: cnt, hits: hits });
    }
    out.armies.push(rec);
  }
  return out;
};
