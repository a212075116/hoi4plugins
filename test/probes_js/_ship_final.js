var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = { 0x2957F28: 'CShip_a', 0x2957F90: 'CShip_b', 0x2962F70: 'CTaskForce_a', 0x2963150: 'CTaskForce_b',
  0x29631C0: 'CTaskForce_c', 0x2963208: 'CTaskForce_d', 0x2962A18: 'CFleet_a', 0x2962A70: 'CFleet_b',
  0x27E7360: 'CCountry', 0x297EA60: 'CCharacter' };
var VTMAP = {};
for (var k in VTN) VTMAP[base.add(parseInt(k)).toString()] = VTN[k];
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || ('?' + v); } catch (e) { return 'ERR'; } }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function chiC(gs) { var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; } return null; }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); return { ok: true, countries: u32(gs, 0x318), chi: cc ? { fleets: u32(cc.c, 0x284), idx: cc.idx } : null }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.run = function () {
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); if (!cc) return { ok: false, err: 'no CHI' };
  var fc = u32(cc.c, 0x284); var fd = cc.c.add(0x278).readPointer();
  var fleets = [];
  for (var j = 0; j < fc; j++) {
    var f = fd.add(8 * j).readPointer();
    var fr = { i: j, ptr: f.toString(), name: cstr(f.add(0xE0)), tfData: null, tfCount: null, tfs: [] };
    var td = u64(f, 0xB8); fr.tfData = td ? td.toString() : null; fr.tfCount = u32(f, 0xC4);
    for (var k = 0; k < (fr.tfCount || 0); k++) {
      var tf = td.add(8 * k).readPointer();
      var sd = u64(tf, 0x728); var sn = u32(tf, 0x734);
      var tr = { i: k, ptr: tf.toString(), vt: vtName(tf), shipsData: sd ? sd.toString() : null, shipCount: sn, ships: [] };
      for (var q = 0; q < (sn || 0); q++) {
        var s = sd.add(8 * q).readPointer();
        tr.ships.push({ i: q, ptr: s.toString(), vt: vtName(s), name: cstr(s.add(0x820)),
                        t98: cstr(s.add(0x98)), tE8: cstr(s.add(0xE8)), tag08: u32(s, 8),
                        hex08: hex(s.add(8), 8), hexVT: hex(s, 8) });
      }
      fr.tfs.push(tr);
    }
    fleets.push(fr);
  }
  return { ok: true, gs: gs.toString(), chiPtr: cc.c.toString(), idx: cc.idx, fleetCount: fc, fleets: fleets };
};
