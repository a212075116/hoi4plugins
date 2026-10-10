var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
function getCam() {
  var obj = base.add(0x332F698).readPointer();
  var cam = obj.add(0x750).readPointer();
  if (cam.isNull()) throw new Error('cam 为空');
  return cam;
}
var camPtr = null;
function snap(cam) {
  return {
    cam: cam.toString(),
    y_674: cam.add(0x674).readFloat(), y_678: cam.add(0x678).readFloat(), y_67c: cam.add(0x67C).readFloat(),
    y_694: cam.add(0x694).readFloat(), y_698: cam.add(0x698).readFloat(), y_69c: cam.add(0x69C).readFloat(), y_6a0: cam.add(0x6A0).readFloat(),
    i0x6d0: cam.add(0x6D0).readS32(), i0x6d4: cam.add(0x6D4).readS32(),
    f0x6fc: cam.add(0x6FC).readFloat(), f0x6f4: cam.add(0x6F4).readFloat()
  };
}
rpc.exports.rd = function () { try { var c = getCam(); camPtr = c; return { ok: true, s: snap(c) }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.wf = function (off, val) { try { var c = camPtr || getCam(); camPtr = c; c.add(off).writeFloat(val); return { ok: true, s: snap(c) }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.wi = function (off, val) { try { var c = camPtr || getCam(); camPtr = c; c.add(off).writeS32(val | 0); return { ok: true, s: snap(c) }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.watch = function (ms) {
  try {
    var c = getCam(); camPtr = c;
    var out = [];
    var t0 = Date.now();
    while (Date.now() - t0 < ms) { out.push(snap(c)); Thread.sleep(0.2); }
    return { ok: true, n: out.length, tail: out.slice(-3) };
  } catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
