var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_RVA = 0x332F698;

var camPtr = null;
function getCam() {
  var gsSlot = base.add(GS_RVA);
  var obj = gsSlot.readPointer();
  if (obj.isNull()) throw new Error('qword_14332F698 为空');
  var vt = obj.readPointer();
  var getter = vt.add(0x130).readPointer();
  var f = new NativeFunction(getter, 'pointer', ['pointer']);
  var cam = f(obj);
  if (cam.isNull()) throw new Error('getter 返回空');
  return cam;
}
function snap(cam) {
  return {
    cam: cam.toString(),
    i0x6c0: cam.add(0x6C0).readS32(),
    i0x6c4: cam.add(0x6C4).readS32(),
    i0x6c8: cam.add(0x6C8).readS32(),
    i0x6cc: cam.add(0x6CC).readS32(),
    i0x6d0: cam.add(0x6D0).readS32(),
    i0x6d4: cam.add(0x6D4).readS32(),
    i0x6d8: cam.add(0x6D8).readS32(),
    i0x6dc: cam.add(0x6DC).readS32(),
    f0x6e8: cam.add(0x6E8).readFloat(),
    f0x6ec: cam.add(0x6EC).readFloat(),
    f0x6f4: cam.add(0x6F4).readFloat(),
    f0x6f8: cam.add(0x6F8).readFloat(),
    f0x6fc: cam.add(0x6FC).readFloat(),
    b0x6f0: cam.add(0x6F0).readU8(),
    v670a: [cam.add(0x670).readFloat(), cam.add(0x674).readFloat(), cam.add(0x678).readFloat()],
    v67ca: [cam.add(0x67C).readFloat(), cam.add(0x680).readFloat(), cam.add(0x684).readFloat()],
    v688a: [cam.add(0x688).readFloat(), cam.add(0x68C).readFloat(), cam.add(0x690).readFloat()],
    v694a: [cam.add(0x694).readFloat(), cam.add(0x698).readFloat(), cam.add(0x69C).readFloat()],
    v6a0a: [cam.add(0x6A0).readFloat(), cam.add(0x6A4).readFloat(), cam.add(0x6A8).readFloat()],
    v700a: [cam.add(0x700).readFloat(), cam.add(0x704).readFloat(), cam.add(0x708).readFloat()],
    v70ca: [cam.add(0x70C).readFloat(), cam.add(0x710).readFloat(), cam.add(0x714).readFloat()],
    v718a: [cam.add(0x718).readFloat(), cam.add(0x71C).readFloat(), cam.add(0x720).readFloat()],
    v724a: [cam.add(0x724).readFloat(), cam.add(0x728).readFloat(), cam.add(0x72C).readFloat()]
  };
}
rpc.exports.snap = function () { try { var c = getCam(); camPtr = c; return { ok: true, s: snap(c) }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.write = function (off, val) { try { var c = camPtr || getCam(); camPtr = c; c.add(off).writeS32(val | 0); return { ok: true, s: snap(c) }; } catch (e) { return { ok: false, err: String(e) }; } };
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
