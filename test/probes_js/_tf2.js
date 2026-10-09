var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = {
  0x2957F28: 'CShip_a', 0x2957F90: 'CShip_b',
  0x2962F70: 'CTaskForce_a', 0x2963150: 'CTaskForce_b', 0x29631C0: 'CTaskForce_c', 0x2963208: 'CTaskForce_d',
  0x2962A18: 'CFleet_a', 0x2962A70: 'CFleet_b',
  0x2971B18: 'CProvince_a', 0x2971B68: 'CProvince_b',
  0x2936CC0: 'CState_a', 0x2936D10: 'CState_b',
  0x27E7360: 'CCountry', 0x297EA60: 'CCharacter',
  0x29530D8: 'CUnit_a', 0x29532B0: 'CUnit_b', 0x2953320: 'CUnit_c',
  0x295A2B0: 'CArmy_a', 0x295A490: 'CArmy_b', 0x295A500: 'CArmy_c', 0x295A548: 'CArmy_d',
  0x2973260: 'CStrategicNavy_a', 0x2973290: 'CStrategicNavy_b', 0x29732E0: 'CStrategicNavyManager'
};
var VTMAP = {}; var VTLIST = [];
for (var kk in VTN) { var pv = base.add(parseInt(kk)); VTMAP[pv.toString()] = VTN[kk]; VTLIST.push(pv); }
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || ('?' + v); } catch (e) { return 'ERR'; } }
function isVt(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || null; } catch (e) { return null; } }
function inHeap(v) { return v.compare(base) < 0 && v.compare(ptr('0x10000000000')) > 0; }
function chiC(gs) {
  var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; }
  return null;
}
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); return { ok: true, countries: u32(gs, 0x318), chi: cc ? { fleets: u32(cc.c, 0x284), idx: cc.idx } : null }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.probeTF = function () {
  try {
    var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); if (!cc) return { ok: false, err: 'no CHI' };
    var fc = u32(cc.c, 0x284); var fd = cc.c.add(0x278).readPointer();
    var out = [];
    for (var j = 0; j < fc; j++) {
      var f = fd.add(8 * j).readPointer();
      var td = u64(f, 0xB8); var tn = u32(f, 0xC4);
      var fr = { fleet: f.toString(), tfData: td ? td.toString() : null, tfCount: tn, tfs: [] };
      for (var k = 0; k < tn; k++) {
        var tf = td.add(8 * k).readPointer();
        var rec = { ptr: tf.toString(), vt: vtName(tf), hex: hex(tf, 0x210), hitLists: [], plain: [] };
        for (var off = 0; off <= 0x208; off += 8) {
          var v = u64(tf, off); if (!v || v.isNull()) continue;
          var selfVt = null; try { selfVt = VTMAP[v.toString()] || null; } catch (e) {}
          if (selfVt) { rec.plain.push({ off: off, kind: 'vtable', name: selfVt }); continue; }
          if (!inHeap(v)) { rec.plain.push({ off: off, kind: 'const', val: v.toString() }); continue; }
          var hits = [];
          for (var q = 0; q < 64; q++) {
            try { var e = v.add(8 * q).readPointer(); if (e.isNull()) continue; var nm = isVt(e); if (nm) hits.push({ i: q, ptr: e.toString(), vt: nm }); } catch (e3) {}
          }
          if (hits.length) rec.hitLists.push({ off: off, data: v.toString(), hits: hits });
          else rec.plain.push({ off: off, kind: 'heap', val: v.toString(), head: hex(v, 16) });
        }
        fr.tfs.push(rec);
      }
      out.push(fr);
    }
    return { ok: true, gs: gs.toString(), chiPtr: cc.c.toString(), fleets: out };
  } catch (e) { return { ok: false, err: String(e) }; }
};
