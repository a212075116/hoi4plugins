'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  peek: function (off, len) {
    const gs = M().base.add(GS).readPointer();
    if (gs.isNull()) return 'CGameState NULL';
    const out = [];
    for (let k = 0; k < len; k++) {
      try { out.push('+0x' + (off + k*4).toString(16) + '=' + gs.add(off + k*4).readS32()); } catch (e) { out.push('ERR'); }
    }
    return out.join('  ');
  },
  // 读日期真源: +0x468 (单位=小时)
  getDate: function () {
    const gs = M().base.add(GS).readPointer();
    const raw = gs.add(0x468).readS32();
    const days = (raw - 43800000) / 24;
    return 'raw=' + raw + '  内部小时偏移=' + (raw - 43800000) + '  天数=' + days;
  },
  setRaw: function (v) {
    const gs = M().base.add(GS).readPointer();
    try {
      Memory.protect(gs.add(0x468), 4, 'rw-');
      gs.add(0x468).writeS32(v);
      return 'wrote +0x468 = ' + v + '  readback=' + gs.add(0x468).readS32();
    } catch (e) { return 'ERR ' + e; }
  },
  addDays: function (d) {
    const gs = M().base.add(GS).readPointer();
    try {
      const old = gs.add(0x468).readS32();
      const nv = old + Math.round(d * 24);
      Memory.protect(gs.add(0x468), 4, 'rw-');
      gs.add(0x468).writeS32(nv);
      return 'old=' + old + ' new=' + nv + ' (+' + d + ' 天)';
    } catch (e) { return 'ERR ' + e; }
  }
};
