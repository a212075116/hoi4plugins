var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT = {
  CShip_a: base.add(0x2957F28), CShip_b: base.add(0x2957F90),
  CTaskForce_a: base.add(0x2962F70), CTaskForce_b: base.add(0x2963150),
  CTaskForce_c: base.add(0x29631C0), CTaskForce_d: base.add(0x2963208),
  CFleet_a: base.add(0x2962A18), CFleet_b: base.add(0x2962A70)
};
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function hex(p, n) { try { var a = new Uint8Array(p.readByteArray(n)); var s = ''; for (var i = 0; i < a.length; i++) { var h = a[i].toString(16); s += (h.length < 2 ? '0' : '') + h; } return s; } catch (e) { return null; } }
function tagOf(t) { if (!t) return null; var s = ''; for (var i = 0; i < 4; i++) { var c = (t >>> (8 * i)) & 0xff; if (c) s += String.fromCharCode(c); } return s; }
function chiC(gs) {
  var carr = gs.add(0x310).readPointer();
  var cnum = u32(gs, 0x318);
  var tp = gs.add(0x358).readPointer();
  var tn = u32(gs, 0x360);
  for (var ci = 0; ci < cnum; ci++) {
    var c = carr.add(8 * ci).readPointer();
    if (c.isNull()) continue;
    if (tagOf(u32(tp, ci * 32)) === 'CHI') return { c: c, idx: ci, n: cnum, tp: tp, tn: tn };
  }
  return null;
}
function candOf(f) {
  var out = [];
  for (var off = 0; off <= 0x128; off += 8) {
    var data = u64(f, off);
    if (!data || data.isNull()) continue;
    var cnt = u32(f, off + 0x0C);
    if (cnt === null || cnt <= 0 || cnt > 300000) continue;
    out.push({ off: off, data: data.toString(), count: cnt });
  }
  return out;
}
rpc.exports.st = function () {
  try {
    var gs = GS_GLOBAL.readPointer();
    if (gs.isNull()) return { ok: false };
    var cc = chiC(gs);
    var info = null;
    if (cc) {
      var fc = u32(cc.c, 0x284);
      var fd = cc.c.add(0x278).readPointer();
      info = { fleets: fc, ptr: cc.c.toString(), idx: cc.idx };
      if (fc > 0 && !fd.isNull()) {
        var f0 = fd.readPointer();
        if (!f0.isNull()) { info.f0 = f0.toString(); info.cands = candOf(f0); }
      }
    }
    return { ok: true, gs: gs.toString(), countries: gs.add(0x318).readU32(), chi: info };
  } catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.scan = function () {
  var wr = Process.enumerateRanges('rw-');
  var out = {};
  for (var k in VT) {
    var pat = VT[k].toMatchPattern();
    var n = 0, samp = [];
    for (var i = 0; i < wr.length; i++) {
      var r = wr[i];
      if (r.size > 256 * 1024 * 1024) continue;
      try { var h = Memory.scanSync(r.base, r.size, pat); n += h.length; for (var j = 0; j < h.length && samp.length < 4; j++) samp.push(h[j].address.toString()); } catch (e) {}
    }
    out[k] = { n: n, samples: samp };
  }
  return out;
};
rpc.exports.dumpChi = function () {
  try {
    var gs = GS_GLOBAL.readPointer();
    var cc = chiC(gs);
    if (!cc) return { ok: false, err: 'CHI not found' };
    var fc = u32(cc.c, 0x284);
    var fd = cc.c.add(0x278).readPointer();
    var fleets = [];
    for (var j = 0; j < fc; j++) {
      var f = fd.add(8 * j).readPointer();
      var o = { i: j, ptr: f.toString(), hex: hex(f, 0x130), name: null, cand: [] };
      try {
        var sz = f.add(0xF0).readU64().toNumber();
        var cap = f.add(0xF8).readU64().toNumber();
        if (sz > 0 && sz < 400) { var dp = (cap <= 15) ? f.add(0xE0) : f.add(0xE0).readPointer(); o.name = dp.readUtf8String(sz); }
      } catch (e) { o.name = null; }
      var cs2 = candOf(f);
      for (var q = 0; q < cs2.length; q++) {
        var c = cs2[q]; var data = ptr(c.data); var elems = [];
        for (var k = 0; k < Math.min(c.count, 12); k++) {
          try { var e2 = data.add(8 * k).readPointer(); if (e2.isNull()) { elems.push(null); continue; } elems.push({ ptr: e2.toString(), vt: hex(e2, 8) }); } catch (e3) { elems.push('ERR'); }
        }
        o.cand.push({ off: c.off, data: c.data, count: c.count, elems: elems });
      }
      fleets.push(o);
    }
    return { ok: true, gs: gs.toString(), chiPtr: cc.c.toString(), idx: cc.idx, fleetCount: fc, fleets: fleets };
  } catch (e) { return { ok: false, err: String(e) }; }
};
