var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_RVA = 0x332F698;
var GETTER_OFF = 0x130;

function dumpBytes(p, n, off0) {
  var out = [];
  var chunk = null;
  try { chunk = new Uint8Array(p.readByteArray(n)); } catch (e) {
    for (var t = n; t >= 16; t = Math.floor(t / 2)) { try { chunk = new Uint8Array(p.readByteArray(t)); n = t; break; } catch (e2) {} }
    if (!chunk) return ['(不可读)'];
  }
  for (var i = 0; i < chunk.length; i += 16) {
    var h = '', a = '';
    for (var j = 0; j < 16 && i + j < chunk.length; j++) {
      var b = chunk[i + j];
      h += (b < 16 ? '0' : '') + b.toString(16) + ' ';
      a += (b >= 32 && b < 127) ? String.fromCharCode(b) : '.';
    }
    out.push(('+0x' + (off0 + i).toString(16)).padEnd(10) + h.padEnd(50) + a);
  }
  return out;
}

rpc.exports.probe = function () {
  var res = { ok: false };
  try {
    var gsSlot = base.add(GS_RVA);
    res.gsSlot = gsSlot.toString();
    var obj = gsSlot.readPointer();
    res.obj = obj.toString();
    if (obj.isNull()) { res.err = 'qword_14332F698 为空'; return res; }
    var vt = obj.readPointer();
    res.vt = vt.toString();
    var modRva = vt.sub(base).toString();
    res.vtRva = modRva;
    var getter = vt.add(GETTER_OFF).readPointer();
    res.getter = getter.toString();
    res.getterRva = getter.sub(base).toString();
    var f = new NativeFunction(getter, 'pointer', ['pointer']);
    var cam = f(obj);
    res.cam = cam.toString();
    if (cam.isNull()) { res.err = 'getter 返回空'; return res; }
    var camVt = cam.readPointer();
    res.camVt = camVt.toString();
    res.camVtRva = camVt.sub(base).toString();
    res.dump = dumpBytes(cam.add(0x600), 0x220, 0x600);
    res.i0x6d0 = cam.add(0x6D0).readS32();
    res.i0x6d4 = cam.add(0x6D4).readS32();
    res.b0x6f0 = cam.add(0x6F0).readU8();
    res.f0x6d0 = cam.add(0x6D0).readFloat();
    res.f0x6d4 = cam.add(0x6D4).readFloat();
    res.ok = true;
  } catch (e) { res.err = String(e) + ' | ' + (e.stack || ''); }
  return res;
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
