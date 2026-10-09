'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  rng: function (lo, hi, span) {
    const m = M();
    const gs = m.base.add(GS).readPointer();
    if (gs.isNull()) return 'CGameState 为 NULL';
    const out = [];
    for (let off = 0; off + 4 <= span; off += 4) {
      try {
        const v = gs.add(off).readS32();
        if (v >= lo && v <= hi) out.push('+0x' + off.toString(16) + '=' + v);
      } catch (e) { }
    }
    return out.length ? out.join(' ') : '(无)';
  },
  // 在更大范围(含堆)找精确值
  exact: function (val) {
    const m = M();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length && out.length < 30; r++) {
      const rg = ranges[r];
      if (rg.size > 0x8000000) continue;
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 0; i + 4 <= u8.length; i += 4) {
          if (dv.getInt32(i, true) === val) {
            out.push(rg.base.add(i) + '  (rva ' + rg.base.add(i).sub(m.base).toString(16) + ')');
            if (out.length >= 30) break;
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到)';
  }
};
