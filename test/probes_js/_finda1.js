'use strict';
const RVA_UI = 0x18A1EE0;
function M() { return Process.getModuleByName('hoi4.exe'); }
let a1s = null;
rpc.exports = {
  ready: function () { return M().base.toString(); },
  install: function () {
    const m = M();
    Interceptor.attach(m.base.add(RVA_UI), {
      onEnter: function (args) {
        try { if (a1s === null) a1s = args[0]; } catch (e) { }
      }
    });
    return 'hooked';
  },
  a1: function () { return a1s ? a1s.toString() : null; },
  // 扫内存找指向 a1 的 qword
  ptrsToA1: function (maxHits) {
    if (!a1s) return 'no a1';
    const m = M();
    const target = a1s;
    const tlo = target.toUInt32();
    const out = [];
    const ranges = Process.enumerateRanges('rw-');
    for (let r = 0; r < ranges.length; r++) {
      const rg = ranges[r];
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        const dv = new DataView(u8.buffer);
        for (let i = 0; i + 8 <= u8.length; i += 8) {
          if (dv.getUint32(i + 4, true) !== 0) continue;
          if (dv.getUint32(i, true) === tlo) {
            const ea = rg.base.add(i);
            const rva = ea.sub(m.base);
            const isImg = (rva.toInt32() > 0 && rva.toInt32() < 0x4000000);
            out.push(ea + (isImg ? '  [IMAGE rva=' + rva.toString() + ']' : '  [heap]'));
            if (out.length >= maxHits) return out.join('\n');
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('\n') : '(未找到)';
  }
};
