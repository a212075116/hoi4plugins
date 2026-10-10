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
rpc.exports.sample = function () {
  try {
    var cam = getCam();
    var out = { cam: cam.toString(), f: [], i: {} };
    for (var off = 0x600; off <= 0x800; off += 4) {
      var v = cam.add(off).readFloat();
      var iv = cam.add(off).readS32();
      out.f.push([off, v, iv]);
    }
    return { ok: true, s: out };
  } catch (e) { return { ok: false, err: String(e) }; }
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
