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
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || null; } catch (e) { return null; } }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
var TARGET = ['Ninghai', 'Hairong', 'Haichen', 'Haichou', 'Zhaohe', 'Yingrui', 'Yu Chang', 'Chien kang', 'Tung An'];
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer(); var chi = null;
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') { chi = { fleets: u32(c, 0x284), idx: ci, ptr: c.toString() }; break; } }
  return { ok: true, countries: cnum, chi: chi }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.hunt = function () {
  var t0 = Date.now();
  var pat = base.add(0x2957F28).toMatchPattern();
  var rs = Process.enumerateRanges('rw-');
  var addrs = [];
  for (var i = 0; i < rs.length; i++) { var r = rs[i]; if (r.size > 256 * 1024 * 1024) continue;
    try { var h = Memory.scanSync(r.base, r.size, pat); for (var j = 0; j < h.length; j++) addrs.push(h[j].address); } catch (e) {} }
  var scanMs = Date.now() - t0;
  var found = [];
  for (var k = 0; k < addrs.length; k++) {
    var s = addrs[k];
    var nm = cstr(s.add(0x820));
    if (!nm || TARGET.indexOf(nm) < 0) continue;
    var rec = { ptr: s.toString(), name: nm, t98: cstr(s.add(0x98)), tag08: u32(s, 8), hex08: hex(s.add(8), 8), refs: [] };
    for (var off = 0; off <= 0x930; off += 8) {
      var v = u64(s, off); if (!v || v.isNull()) continue;
      var nm2 = vtName(v);
      if (nm2) { rec.refs.push({ off: off, val: v.toString(), vt: nm2 }); continue; }
      if (v.compare(base) < 0 && v.compare(ptr('0x10000000000')) > 0) rec.refs.push({ off: off, val: v.toString(), vt: '?(heap)' });
    }
    found.push(rec);
  }
  return { ok: true, total: addrs.length, scanMs: scanMs, matchMs: Date.now()-t0-scanMs, found: found };
};
