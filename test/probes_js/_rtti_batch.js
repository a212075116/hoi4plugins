var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
// 读 NUL 结尾的 ASCII/Latin-1 串: 逐字节找 NUL, 不用 readUtf8String(它读固定长度)
function readName(p, max) {
  var n = max || 512;
  var buf = null;
  try { buf = new Uint8Array(p.readByteArray(n)); } catch (e) {
    for (var t = n; t >= 16; t = Math.floor(t / 2)) { try { buf = new Uint8Array(p.readByteArray(t)); break; } catch (e2) {} }
    if (!buf) return null;
  }
  var s = '';
  for (var i = 0; i < buf.length; i++) { if (buf[i] === 0) break; s += String.fromCharCode(buf[i]); }
  return s;
}
function u32v(v) { return v === null ? null : (v >>> 0); }
function rttiOf(vtAddr) {
  var o = { vt: vtAddr };
  try {
    var vt = ptr(vtAddr);
    var col = u64(vt, -8);
    if (!col || col.isNull()) { o.err = 'noCOL'; return o; }
    o.col = col.toString();
    o.sig = u32v(u32(col, 0));
    o.off = u32v(u32(col, 4));
    var tdRva = u32v(u32(col, 0x0C));
    o.tdRva = tdRva;
    if (tdRva === null || tdRva === 0) { o.err = 'noTD'; return o; }
    o.name = readName(base.add(tdRva).add(0x10), 512);
    o.ok = true;
  } catch (e) { o.err = String(e); }
  return o;
}
rpc.exports.batch = function (rvas) {
  var out = [];
  for (var i = 0; i < rvas.length; i++) {
    var rva = rvas[i];
    var a;
    try { a = base.add(rva).toString(); } catch (e) { out.push({ rva: rva, err: 'badRva' }); continue; }
    var r = rttiOf(a); r.rva = rva; out.push(r);
  }
  return out;
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
