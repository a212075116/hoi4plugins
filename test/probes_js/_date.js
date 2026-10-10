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
  getDate: function () {
    const gs = M().base.add(GS).readPointer();
    const raw = gs.add(0x468).readS32();
    return 'raw=' + raw + ' 天数=' + ((raw - 43800000) / 24);
  },
  setRaw: function (v) {
    const gs = M().base.add(GS).readPointer();
    try {
      Memory.protect(gs.add(0x468), 4, 'rw-');
      gs.add(0x468).writeS32(v);
      return 'wrote raw=' + v + '  readback=' + gs.add(0x468).readS32();
    } catch (e) { return 'ERR ' + e; }
  },
  find: function (v, lo, hi) {
    const gs = M().base.add(GS).readPointer();
    const out = [];
    for (let off = lo; off + 4 <= hi; off += 4) {
      try { if (gs.add(off).readS32() === v) out.push('+0x' + off.toString(16)); } catch (e) { }
    }
    return out.join(' ') || '(无)';
  },
  poke: function (off, v) {
    const gs = M().base.add(GS).readPointer();
    try {
      Memory.protect(gs.add(off), 4, 'rw-');
      gs.add(off).writeS32(v);
      return 'wrote +0x' + off.toString(16) + '=' + v + ' rb=' + gs.add(off).readS32();
    } catch (e) { return 'ERR ' + e; }
  }
};
