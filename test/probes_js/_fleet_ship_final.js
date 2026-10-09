var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = { 0x2957F28: 'CShip_a', 0x2957F90: 'CShip_b', 0x2962F70: 'CTaskForce_a', 0x2963150: 'CTaskForce_b',
  0x29631C0: 'CTaskForce_c', 0x2963208: 'CTaskForce_d', 0x2962A18: 'CFleet_a', 0x2962A70: 'CFleet_b',
  0x27E7360: 'CCountry' };
var VTMAP = {};
for (var k in VTN) VTMAP[base.add(parseInt(k)).toString()] = VTN[k];
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || ('?' + v); } catch (e) { return 'ERR'; } }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function chiC(gs) { var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; } return null; }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); return { ok: true, countries: u32(gs, 0x318), chi: cc ? { fleets: u32(cc.c, 0x284), idx: cc.idx } : null }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.run = function () {
  var t0 = Date.now();
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); if (!cc) return { ok: false, err: 'no CHI' };
  var fc = u32(cc.c, 0x284); var fd = cc.c.add(0x278).readPointer();
  var tfs = {}; var tfList = [];
  for (var j = 0; j < fc; j++) {
    var f = fd.add(8 * j).readPointer();
    var fname = cstr(f.add(0xE0)); var fref = u32(f, 0x0C);
    var td = u64(f, 0xB8); var tn = u32(f, 0xC4);
    var sub = [];
    for (var k = 0; k < (tn || 0); k++) {
      var tf = td.add(8 * k).readPointer();
      var key = tf.toString();
      var info = { fleet: f.toString(), fleetName: fname, fleetRef: fref, fleetIdx: j, tfIdx: k, tfPtr: key };
      tfs[key] = info; sub.push(info);
    }
    tfList.push({ fleet: f.toString(), name: fname, ref: fref, idx: j, tfCount: tn, tfs: sub });
  }
  var pat = base.add(0x2957F28).toMatchPattern();
  var rs = Process.enumerateRanges('rw-');
  var addrs = [];
  for (var i = 0; i < rs.length; i++) { var r = rs[i]; if (r.size > 256 * 1024 * 1024) continue;
    try { var h = Memory.scanSync(r.base, r.size, pat); for (var q = 0; q < h.length; q++) addrs.push(h[q].address); } catch (e) {} }
  var scanMs = Date.now() - t0;
  var ships = []; var otherTf = {};
  for (var m = 0; m < addrs.length; m++) {
    var s = addrs[m]; var back = u64(s, 0x728);
    if (!back || back.isNull()) continue;
    var key2 = back.toString();
    var info2 = tfs[key2];
    if (!info2) { otherTf[key2] = (otherTf[key2] || 0) + 1; continue; }
    ships.push({ ptr: s.toString(), name: cstr(s.add(0x820)), t98: cstr(s.add(0x98)), tE8: cstr(s.add(0xE8)),
                 tag08: u32(s, 8), vt: vtName(s), tf: key2, tfVt: vtName(back),
                 fleet: info2.fleet, fleetName: info2.fleetName, fleetRef: info2.fleetRef, tfIdx: info2.tfIdx });
  }
  return { ok: true, gs: gs.toString(), chiPtr: cc.c.toString(), idx: cc.idx, total: addrs.length,
           scanMs: scanMs, totalMs: Date.now() - t0, tfList: tfList, ships: ships, otherTfCount: Object.keys(otherTf).length };
};
