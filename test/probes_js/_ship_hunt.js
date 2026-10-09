var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function cstr(p) { try { var sz = p.add(0x10).readU64().toNumber(); var cap = p.add(0x18).readU64().toNumber(); if (sz <= 0 || sz > 400 || cap < sz) return null; var dp = (cap <= 15) ? p : p.readPointer(); return dp.readUtf8String(sz); } catch (e) { return null; } }
function chiC(gs) {
  var carr = gs.add(0x310).readPointer(); var cnum = u32(gs, 0x318); var tp = gs.add(0x358).readPointer();
  for (var ci = 0; ci < cnum; ci++) { var c = carr.add(8 * ci).readPointer(); if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci }; }
  return null;
}
rpc.exports.st = function () { try { var gs = GS_GLOBAL.readPointer(); if (gs.isNull()) return { ok: false };
  var cc = chiC(gs); return { ok: true, countries: u32(gs, 0x318), chi: cc ? { fleets: u32(cc.c, 0x284), idx: cc.idx } : null }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.hunt = function () {
  var t0 = Date.now();
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); var chiPtr = cc.c;
  var pat = base.add(0x2957F28).toMatchPattern();
  var rs = Process.enumerateRanges('rw-');
  var addrs = [];
  for (var i = 0; i < rs.length; i++) {
    var r = rs[i]; if (r.size > 256 * 1024 * 1024) continue;
    try { var h = Memory.scanSync(r.base, r.size, pat); for (var j = 0; j < h.length; j++) addrs.push(h[j].address); } catch (e) {}
  }
  var scanMs = Date.now() - t0;
  var chiShips = [];
  for (var k = 0; k < addrs.length; k++) {
    var s = addrs[k]; var offs = [];
    for (var off = 0; off <= 0x900; off += 8) {
      var v = u64(s, off); if (!v) continue;
      if (v.equals(chiPtr)) offs.push(off);
    }
    if (offs.length) chiShips.push({ ptr: s.toString(), chiOff: offs });
  }
  return { ok: true, total: addrs.length, scanMs: scanMs, chiPtr: chiPtr.toString(), chiShips: chiShips };
};
rpc.exports.dumpShip = function (addr) {
  var s = ptr(addr);
  var o = { ptr: addr, hex: hex(s, 0x900), strs: [], ptrs: [] };
  for (var off = 0; off <= 0x8F8; off += 8) {
    var v = u64(s, off); if (!v || v.isNull()) continue;
    if (!v.compare(base) || v.compare(base) > 0) { o.ptrs.push({ off: off, val: v.toString(), kind: 'code' }); continue; }
    if (v.compare(ptr('0x10000000000')) < 0) { o.ptrs.push({ off: off, val: v.toString(), kind: 'const' }); continue; }
    o.ptrs.push({ off: off, val: v.toString(), kind: 'heap' });
  }
  return o;
};
rpc.exports.scanStrings = function () {
  var t0 = Date.now();
  var gs = GS_GLOBAL.readPointer(); var cc = chiC(gs); var chiPtr = cc.c;
  var pat = base.add(0x2957F28).toMatchPattern();
  var rs = Process.enumerateRanges('rw-');
  var addrs = [];
  for (var i = 0; i < rs.length; i++) {
    var r = rs[i]; if (r.size > 256 * 1024 * 1024) continue;
    try { var h = Memory.scanSync(r.base, r.size, pat); for (var j = 0; j < h.length; j++) addrs.push(h[j].address); } catch (e) {}
  }
  var out = [];
  for (var k = 0; k < addrs.length; k++) {
    var s = addrs[k]; var found = [];
    for (var off = 0; off <= 0x8E0; off += 8) {
      var nm = cstr(s.add(off));
      if (nm && nm.length >= 2 && nm.length <= 60) found.push({ off: off, name: nm });
    }
    var isChi = false; var chiOff = null;
    for (var off2 = 0; off2 <= 0x900; off2 += 8) { var v = u64(s, off2); if (v && v.equals(chiPtr)) { isChi = true; chiOff = off2; break; } }
    out.push({ ptr: s.toString(), chi: isChi, chiOff: chiOff, names: found });
  }
  return { ok: true, total: addrs.length, ms: Date.now() - t0, ships: out };
};
