'use strict';
rpc.exports = {
  hex: function (rva, n) {
    const m = Process.getModuleByName('hoi4.exe');
    const b = m.base.add(rva).readByteArray(n);
    const u8 = new Uint8Array(b);
    let s = '';
    for (let i = 0; i < u8.length; i++) s += ('0' + u8[i].toString(16)).slice(-2) + ' ';
    return s;
  },
  txt: function (rva, n) {
    const m = Process.getModuleByName('hoi4.exe');
    let s = '';
    for (let i = 0; i < n; i++) {
      const c = m.base.add(rva + i).readU8();
      s += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
    }
    return s;
  }
};
