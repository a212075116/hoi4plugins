'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  // 扫内存找内容等于 target 的 8 字节 (即指向 target 的指针)
  ptrsTo: function (targetStr, maxHits) {
    const target = ptr(targetStr);
    const m = M();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length; r++) {
      const rg = ranges[r];
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 0; i + 8 <= u8.length; i += 8) {
          const lo = dv.getUint32(i, true);
          const hi = dv.getUint32(i + 4, true);
          if (hi !== 0) continue;
          const v = lo;
          if (v === target.toUInt32()) {
            const ea = rg.base.add(i);
            let where = 'heap';
            const rva = ea.sub(m.base);
            if (rva.toInt32() > 0 && rva.toInt32() < 0x4000000) where = 'IMAGE rva=' + rva.toString();
            out.push(ea + '  [' + where + ']');
            if (out.length >= maxHits) return out.join('\n');
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到指向它的指针)';
  },
  // 也找 image 内的 32 位 rva 引用 (静态基址 + 偏移)
  statics: function (targetStr) {
    const target = ptr(targetStr);
    const m = M();
    const t32 = target.toUInt32();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length; r++) {
      const rg = ranges[r];
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 0; i + 4 <= u8.length; i += 4) {
          if (dv.getUint32(i, true) === t32) {
            const ea = rg.base.add(i);
            const rva = ea.sub(m.base);
            const isImg = (rva.toInt32() > 0 && rva.toInt32() < 0x4000000);
            out.push(ea + (isImg ? '  [IMAGE rva=' + rva.toString() + ']' : '  [heap]'));
            if (out.length >= 60) return out.join('\n');
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到)';
  }
};
