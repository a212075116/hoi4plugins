'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  hex: function (rva, n) {
    const u8 = new Uint8Array(M().base.add(rva).readByteArray(n));
    let s = '';
    for (let i = 0; i < u8.length; i++) {
      s += ('0' + u8[i].toString(16)).slice(-2) + ' ';
      if ((i + 1) % 16 === 0) s += '\n';
    }
    return s;
  },
  // 算 rip 相对目标
  rip: function (insnRva, insnLen, disp) { return insnRva + insnLen + disp; },
  u32: function (rva) { return M().base.add(rva).readU32(); }
  asStr: function (rva) { try { return M().base.add(rva).readUtf8String(); } catch (e) { return 'ERR'; } }
};
