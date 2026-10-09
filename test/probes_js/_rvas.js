'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  find: function (needle) {
    const m = M();
    const out = [];
    const pat = [];
    for (let i = 0; i < needle.length; i++) pat.push(needle.charCodeAt(i));
    const rgs = Process.enumerateRanges('r--');
    for (let r = 0; r < rgs.length; r++) {
      const rg = rgs[r];
      if (rg.size > 0x4000000) continue;
      try {
        const u8 = new Uint8Array(rg.base.readByteArray(rg.size));
        for (let i = 0; i + pat.length < u8.length; i++) {
          let ok = true;
          for (let k = 0; k < pat.length; k++) if (u8[i + k] !== pat[k]) { ok = false; break; }
          if (ok && u8[i + pat.length] === 0) {
            out.push('rva=' + rg.base.add(i).sub(m.base).toString(16));
            if (out.length >= 6) return out.join('  ');
          }
        }
      } catch (e) { }
    }
    return out.length ? out.join('  ') : '(未找到)';
  }
};
