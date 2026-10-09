'use strict';
const TXT_RVA = 0x1000, TXT_SIZE = 0x27050d8;
rpc.exports = {
  scan: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const buf = m.base.add(TXT_RVA).readByteArray(TXT_SIZE);
    const u8 = new Uint8Array(buf);
    const dv = new DataView(buf);
    const out = [];
    for (let i = 0; i + 8 < u8.length; i++) {
      const op = u8[i];
      // 89 /r  mov r/m32, r32 ; 只有 89 (不是 8b)
      if (op !== 0x89) continue;
      const modrm = u8[i + 1];
      const mod = modrm >> 6, rm = modrm & 7;
      if (mod !== 2 || rm === 4) continue;
      const disp = dv.getInt32(i + 2, true);
      if (disp !== 0x50) continue;
      const lo = Math.max(0, i - 26);
      let ctx = '';
      for (let k = lo; k < i; k++) ctx += ('0' + u8[k].toString(16)).slice(-2) + ' ';
      out.push('rva=' + (TXT_RVA + i).toString(16) + '  modrm=' + modrm.toString(16) + '  ...' + ctx);
      if (out.length > 50) break;
    }
    return out.length ? out.join('\n') : '(none)';
  }
};
