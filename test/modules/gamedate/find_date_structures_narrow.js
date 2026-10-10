'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  // 特征: [p-8] in 28..31, [p] in 490..530, [p+4] in 3000..9000
  scan: function (maxHits) {
    const m = M();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length && out.length < maxHits; r++) {
      const rg = ranges[r];
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 8; i + 16 <= u8.length; i += 4) {
          const md = dv.getInt32(i - 8, true);
          if (md < 28 || md > 31) continue;
          const y = dv.getInt32(i, true);
          if (y < 490 || y > 530) continue;
          const v4 = dv.getInt32(i + 4, true);
          if (v4 < 3000 || v4 > 9000) continue;
          const ea = rg.base.add(i);
          const rva = ea.sub(m.base);
          if (rva.toInt32() > 0 && rva.toInt32() < 0x4000000) continue;
          out.push(ea + '  y=' + y + ' md=' + md + ' p4=' + v4);
          if (out.length >= maxHits) break;
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到)';
  }
};
