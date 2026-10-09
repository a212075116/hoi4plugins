var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
function hexPat(addr) {
  var h = addr.toString(16);
  while (h.length < 16) h = '0' + h;
  var b = [];
  for (var i = 14; i >= 0; i -= 2) b.push(h.substr(i, 2));
  return b.join(' ');
}
function pointersInRange(p, n) {
  var out = [];
  for (var k = 0; k < n; k += 8) {
    try { var q = p.add(k).readPointer(); out.push({ off: k, v: q.toString() }); } catch (e) { out.push({ off: k, v: 'ERR' }); }
  }
  return out;
}
function fl(p, n) {
  var out = [];
  for (var k = 0; k < n; k += 4) {
    try { out.push({ off: k, f: p.add(k).readFloat() }); } catch (e) { out.push({ off: k, f: null }); }
  }
  return out;
}
rpc.exports.scan = function (spec) {
  var ranges = Process.enumerateRanges('rw-');
  var res = {};
  for (var t = 0; t < spec.length; t++) {
    var name = spec[t].name, rva = spec[t].rva;
    var vt = base.add(rva);
    var pat = hexPat(vt);
    var hits = [];
    for (var i = 0; i < ranges.length; i++) {
      var r = ranges[i];
      if (r.size > 512 * 1024 * 1024) continue;
      try {
        var m = Memory.scanSync(r.base, r.size, pat);
        for (var j = 0; j < m.length; j++) hits.push({ addr: m[j].address.toString(), size: r.size });
      } catch (e) {}
    }
    res[name] = { rva: rva, vt: vt.toString(), hits: hits.length, sample: hits.slice(0, 12) };
  }
  return res;
};
rpc.exports.dump = function (addr, n) {
  var p = ptr(addr);
  return { addr: addr, ptrs: pointersInRange(p, n || 0x100), floats: fl(p, n || 0x100) };
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
