var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
rpc.exports.gs = function () {
  var r = { ok: false, base: base.toString() };
  try {
    var slot = base.add(0x332F260);
    r.slot = slot.toString();
    // 先当作【对象本体】读
    var asObj_country = slot.add(0x310).readPointer();
    var asObj_n = slot.add(0x318).readS32();
    r.asObject = { countries: asObj_country.toString(), count: asObj_n };
    // 再当作【指针】读一次
    var p = slot.readPointer();
    r.asPointer_value = p.toString();
    if (!p.isNull()) {
      try {
        var p2 = p.add(0x310).readPointer();
        var n2 = p.add(0x318).readS32();
        r.asPointerDeref = { countries: p2.toString(), count: n2 };
      } catch (e) { r.asPointerDeref = 'unreadable: ' + e; }
    }
    r.ok = true;
  } catch (e) { r.err = String(e); }
  return r;
};
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
