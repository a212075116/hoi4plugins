'use strict';
const TXT_RVA = 0x1000, TXT_SIZE = 0x27050d8;
const T = [0x297e370];
rpc.exports = {
  scan: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const buf = m.base.add(TXT_RVA).readByteArray(TXT_SIZE);
    const u8 = new Uint8Array(buf);
    const dv = new DataView(buf);
    const out = [];
    for (let i = 4; i + 4 <= u8.length; i++) {
      const disp = dv.getInt32(i, true);
      const tgt = (TXT_RVA + i + 4 + disp) >>> 0;
      if (T.indexOf(tgt) < 0) continue;
      const lo = Math.max(0, i - 8);
      let ctx = '';
      for (let k = lo; k < i; k++) ctx += ('0' + u8[k].toString(16)).slice(-2) + ' ';
      out.push('rva=' + (TXT_RVA + i - 3).toString(16) + '  ' + ctx + ' -> vt 0x297e370');
      if (out.length > 30) break;
    }
    return out.length ? out.join('\n') : '(none)';
  }
};
