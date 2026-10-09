'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
const RVA_MONTHTAB = 0x3085210;
const RVA_PARSE    = 0x0533D60;
const RVA_GS       = 0x332F260;
rpc.exports = {
  ready: function () { return M().base.toString(); },
  tab: function () {
    const m = M();
    const out = [];
    for (let i = 0; i < 16; i++) {
      try { out.push(i + ':' + m.base.add(RVA_MONTHTAB + i*4).readS32()); } catch (e) { out.push(i + ':ERR'); }
    }
    return 'monthtab @' + m.base.add(RVA_MONTHTAB) + '  ' + out.join(' ');
  },
  gsdate: function () {
    const m = M();
    const gs = m.base.add(RVA_GS).readPointer();
    if (gs.isNull()) return 'gs NULL';
    return 'CGameDate obj=' + gs.add(0x460) + '  raw(+0x468)=' + gs.add(0x468).readS32();
  },
  // 直接用 C 里的方式: 构造 std::string 调 sub_140533D60
  callParse: function (text) {
    const m = M();
    const gs = m.base.add(RVA_GS).readPointer();
    if (gs.isNull()) return 'gs NULL';
    const obj = gs.add(0x460);
    const n = text.length;
    const buf = Memory.alloc(32);
    for (let i = 0; i < 32; i++) buf.add(i).writeU8(0);
    buf.writeUtf8String(text);
    buf.add(0x10).writeU64(n);
    buf.add(0x18).writeU64(15);
    const before = gs.add(0x468).readS32();
    const fn = new NativeFunction(m.base.add(RVA_PARSE), 'char', ['pointer','pointer']);
    let r = -1;
    let err = null;
    try { r = fn(obj, buf); } catch (e) { err = String(e); }
    const after = gs.add(0x468).readS32();
    return 'parse("' + text + '") ret=' + r + ' err=' + err + '  raw ' + before + ' -> ' + after;
  }
};
