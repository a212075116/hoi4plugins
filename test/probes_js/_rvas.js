'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  vt: function (rva, n) {
    const m = M();
    const out = [];
    for (let i = 0; i < n; i++) {
      try {
        const v = m.base.add(rva + i * 8).readPointer();
        let r = -1;
        try { r = v.sub(m.base).toInt32(); } catch (e) { }
        out.push('[' + i + '] +0x' + (i * 8).toString(16) + '  rva=' + (r > 0 && r < 0x3800000 ? r.toString(16) : '?'));
      } catch (e) { out.push('[' + i + '] ERR'); }
    }
    return out.join('\n');
  },
  hex: function (rva, n) {
    const u8 = new Uint8Array(M().base.add(rva).readByteArray(n));
    let s = '';
    for (let i = 0; i < u8.length; i++) { s += ('0' + u8[i].toString(16)).slice(-2) + ' '; if ((i+1) % 16 === 0) s += '\n'; }
    return s;
  }
};
