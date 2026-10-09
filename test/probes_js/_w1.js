var m = Process.enumerateModules(), exe = null;
for (var i = 0; i < m.length; i++) if (m[i].name.toLowerCase() === 'hoi4.exe') exe = m[i];
var base = exe.base;
function getCam() {
  var gs = base.add(0x332F260).readPointer();
  var obj = base.add(0x332F698).readPointer();
  var cam = obj.add(0x750).readPointer();
  return { gs: gs, obj: obj, cam: cam };
}
function snap(c) {
  return {
    f678: c.add(0x678).readFloat(),
    f69c: c.add(0x69C).readFloat(),
    f684: c.add(0x684).readFloat(),
    i6d0: c.add(0x6D0).readS32(),
    i6d4: c.add(0x6D4).readS32(),
    f6fc: c.add(0x6FC).readFloat(),
    f674: c.add(0x674).readFloat(),
    f67c: c.add(0x67C).readFloat()
  };
}
rpc.exports.rd = function () {
  try { var h = getCam(); return { ok: true, hs: { gs: h.gs.toString(), obj: h.obj.toString(), cam: h.cam.toString() }, s: snap(h.cam) }; }
  catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.wf = function (off, v) {
  try { var h = getCam(); h.cam.add(off).writeFloat(v); return { ok: true, s: snap(h.cam) }; }
  catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
