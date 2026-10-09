var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VTN = { 0x27E7360: 'CCountry', 0x295A2B0: 'CArmy_a', 0x295A490: 'CArmy_b', 0x295A500: 'CArmy_c', 0x295A548: 'CArmy_d' };
var VTMAP = {}; for (var k in VTN) VTMAP[base.add(parseInt(k)).toString()] = VTN[k];
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function vtName(p) { try { var v = p.readPointer().toString(); return VTMAP[v] || null; } catch (e) { return null; } }
function chiC(gs) { var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; } return null; }
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); if (!cc) return { ok: true, chi: null };
  return { ok: true, chi: { armies: u32(cc.c, 0x29C) } }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.full = function () {
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); if (!cc) return { ok: false };
  var ad = u64(cc.c, 0x290); var an = u32(cc.c, 0x29C);
  var out = [];
  for (var i = 0; i < an; i++) {
    var a = ad.add(8 * i).readPointer();
    var o = { i: i, ptr: a.toString(), vt: vtName(a), id1C: u32(a, 0x1C), loc28: u32(a, 0x28), loc2C: u32(a, 0x2C),
              loc30: (u64(a,0x30) ? u64(a,0x30).toString() : null), tmpl: null, tmplVia: null, unit: null, kind: null,
              v18: u32(a, 0x18), n20: u32(a, 0x20), n24: u32(a, 0x24), n34: u32(a, 0x34), n38: u32(a, 0x38) };
    for (var off = 0; off + 0x20 <= 0x800; off += 8) {
      var nm = cstr(a.add(off));
      if (!nm) continue;
      if (!o.kind && (nm === 'infantry' || nm === 'cavalry' || nm === 'motorized' || nm === 'armor')) o.kind = nm;
    }
    for (var off2 = 0; off2 + 8 <= 0x800; off2 += 8) {
      var v = u64(a, off2); if (!v || v.isNull()) continue;
      if (v.compare(base) >= 0 || v.compare(ptr('0x10000000000')) <= 0) continue;
      if (!o.tmpl) { var t2 = cstr(v.add(0x20)); if (t2 && t2.length <= 60) { o.tmpl = t2; o.tmplVia = off2; } }
      if (!o.unit) { var t1 = cstr(v.add(0x60)); if (t1 && t1.length <= 60) { o.unit = t1; } }
    }
    out.push(o);
  }
  return { ok: true, count: an, armies: out };
};
