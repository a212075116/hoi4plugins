var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = {
  0x27E7360: 'CCountry', 0x2962A18: 'CFleet_a', 0x2957F28: 'CShip_a', 0x2962F70: 'CTaskForce_a',
  0x295A2B0: 'CArmy_a', 0x295A490: 'CArmy_b', 0x295A500: 'CArmy_c', 0x295A548: 'CArmy_d',
  0x29530D8: 'CUnit_a', 0x29532B0: 'CUnit_b', 0x2953320: 'CUnit_c',
  0x2971B18: 'CProvince_a', 0x2936CC0: 'CState_a'
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
  return { ok: true, chi: { fleets: u32(cc.c, 0x284), armies: u32(cc.c, 0x29C), idx: cc.idx } }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.findStr = function (s) {
  var t0 = Date.now();
  var rs = Process.enumerateRanges('rw-');
  var hits = [];
  for (var i = 0; i < rs.length; i++) { var r = rs[i]; if (r.size > 256 * 1024 * 1024) continue;
    try { var h = Memory.scanSync(r.base, r.size, s); for (var j = 0; j < h.length; j++) hits.push(h[j].address.toString()); } catch (e) {} }
  return { ok: true, s: s, ms: Date.now() - t0, hits: hits };
};
rpc.exports.probeAround = function (addr, back, fwd) {
  var p = ptr(addr);
  var b = back || 0x400; var f = fwd || 0x400;
  var st = p.sub(b);
  var o = { addr: addr, start: st.toString(), len: b + f, hex: hex(st, b + f), vtHits: [], names: [] };
  for (var off = 0; off + 8 <= b + f; off += 8) {
    var q = st.add(off);
    var v = u64(q, 0);
    if (v && !v.isNull()) { var nm = vtName(v); if (nm) o.vtHits.push({ off: off - b, val: v.toString(), vt: nm }); }
    var nm2 = cstr(q); if (nm2 && nm2.length >= 2 && nm2.length <= 80) o.names.push({ off: off - b, name: nm2 });
  }
  return o;
};
