'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  peek: function (off, len) {
    const gs = M().base.add(GS).readPointer();
    if (gs.isNull()) return 'gs NULL';
    const out = [];
    for (let k = 0; k < len; k++) {
      try { out.push('+0x' + (off + k*4).toString(16) + '=' + gs.add(off + k*4).readS32()); } catch (e) { out.push('ERR'); }
    }
    return out.join('  ');
  },
  // 在 CGameState 前 0x8000 里找值 v
  find: function (v, span) {
    const gs = M().base.add(GS).readPointer();
    const out = [];
    for (let off = 0; off + 4 <= span; off += 4) {
      try { if (gs.add(off).readS32() === v) out.push('+0x' + off.toString(16)); } catch (e) { }
    }
    return out.join(' ') || '(无)';
  },
  // 全堆扫某值 (限制块大小)
  findHeap: function (v, maxHits) {
    const m = M();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length && out.length < maxHits; r++) {
      const rg = ranges[r];
      if (rg.size > 0x2000000) continue;
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 0; i + 4 <= u8.length; i += 4) {
          if (dv.getInt32(i, true) === v) {
            out.push(rg.base.add(i) + ' (rva ' + rg.base.add(i).sub(m.base).toString(16) + ')');
            if (out.length >= maxHits) break;
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到)';
  }
};
