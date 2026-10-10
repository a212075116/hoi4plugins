'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  // 同时读两边
  both: function (otherAddr) {
    const m = M();
    const gs = m.base.add(GS).readPointer();
    let s = 'CGameState+0x468(raw)=' + gs.add(0x468).readS32();
    s += '  +0x478(年)=' + gs.add(0x478).readS32();
    s += '  +0x480(日)=' + gs.add(0x480).readS32();
    s += '  +0x488(月-1)=' + gs.add(0x488).readS32();
    try { s += '  |  你那个=' + ptr(otherAddr).readS32(); } catch (e) { s += '  |  你那个=ERR'; }
    return s;
  }
};
