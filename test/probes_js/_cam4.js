var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
rpc.exports.verify = function () {
  var res = {};
  try {
    var slot = base.add(0x332F698);
    res.slot_abs = slot.toString();
    var obj = slot.readPointer();
    res.obj = obj.toString();
    var camDirect = obj.add(0x750).readPointer();
    res.obj_plus_0x750 = camDirect.toString();
    res.obj_plus_0x750_rva = camDirect.sub(base).toString();
    // 用虚表 getter 再取一次做交叉验证
    var vt = obj.readPointer();
    res.obj_vt = vt.toString();
    var getter = vt.add(0x130).readPointer();
    var f = new NativeFunction(getter, 'pointer', ['pointer']);
    var camViaVt = f(obj);
    res.cam_via_getter = camViaVt.toString();
    res.same = (camDirect.equals(camViaVt));
    res.i0x6d0 = camDirect.add(0x6D0).readS32();
    res.i0x6d4 = camDirect.add(0x6D4).readS32();
    res.i0x6c8 = camDirect.add(0x6C8).readS32();
    res.i0x6cc = camDirect.add(0x6CC).readS32();
    res.b0x6f0 = camDirect.add(0x6F0).readU8();
    res.f0x6fc = camDirect.add(0x6FC).readFloat();
    // 顺便读全局 clamp 开关
    res.clamp_b1430B2E30 = base.add(0x30B2E30).readU8();
    res.ok = true;
  } catch (e) { res.err = String(e); }
  return res;
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
