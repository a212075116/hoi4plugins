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
  0x27E7360: 'CCountry', 0x297EA60: 'CCharacter'
};
var VTMAP = {};
for (var k in VTN) VTMAP[base.add(parseInt(k)).toString()] = VTN[k];
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || ('?' + v); } catch (e) { return 'ERR'; } }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function chiC(gs) {
  var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) {
    var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci };
  }
  return null;
}
function candOf(o, maxElems) {
  var out = [];
  for (var off = 0; off <= 0x1F0; off += 8) {
    var data = u64(o, off); if (!data || data.isNull()) continue;
    var cnt = u32(o, off + 0x0C);
    if (cnt === null || cnt <= 0 || cnt > 3000) continue;
    var elems = [], ok = 0;
    for (var k = 0; k < Math.min(cnt, maxElems); k++) {
      try { var e = data.add(8 * k).readPointer(); if (e.isNull()) { elems.push(null); continue; } elems.push({ ptr: e.toString(), vt: vtName(e) }); ok++; } catch (e2) { elems.push('ERR'); }
    }
    if (ok > 0) out.push({ off: off, data: data.toString(), count: cnt, elems: elems });
  }
  return out;
}
rpc.exports.st = function () {
  try {
    var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
    var cc = chiC(gs); var info = null;
    if (cc) info = { fleets: u32(cc.c, 0x284), idx: cc.idx, ptr: cc.c.toString() };
    return { ok: true, countries: u32(gs, 0x318), chi: info };
  } catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.dumpTF = function () {
  try {
    var gs = GS_GLOBAL.readPointer();
    var cc = chiC(gs); if (!cc) return { ok: false, err: 'CHI not found' };
    var fc = u32(cc.c, 0x284); var fd = cc.c.add(0x278).readPointer();
    var fleets = [];
    for (var j = 0; j < fc; j++) {
      var f = fd.add(8 * j).readPointer();
      var fr = { i: j, ptr: f.toString(), name: cstr(f.add(0xE0)), tfData: null, tfCount: null, tfs: [] };
      var td = u64(f, 0xB8); fr.tfData = td ? td.toString() : null; fr.tfCount = u32(f, 0xC4);
      if (td && !td.isNull() && fr.tfCount > 0 && fr.tfCount < 1000) {
        for (var k = 0; k < fr.tfCount; k++) {
          var tf = td.add(8 * k).readPointer();
          fr.tfs.push({ i: k, ptr: tf.toString(), vt: vtName(tf), hex: hex(tf, 0x200), cand: candOf(tf, 16) });
        }
      }
      fleets.push(fr);
    }
    return { ok: true, gs: gs.toString(), chiPtr: cc.c.toString(), idx: cc.idx, fleetCount: fc, fleets: fleets };
  } catch (e) { return { ok: false, err: String(e) }; }
};
