'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  asStr: function (rva) { try { return M().base.add(rva).readUtf8String(); } catch (e) { return 'ERR'; } },
  vt: function (rva, n) {
    const m = M();
    const out = [];
    for (let i = 0; i < n; i++) {
      try {
        const v = m.base.add(rva + i * 8).readPointer();
        let r = -1;
        try { r = v.sub(m.base).toInt32(); } catch (e) { }
        out.push('  [' + i + '] +0x' + (i * 8).toString(16) + '  ' + (r > 0 && r < 0x3800000 ? 'rva ' + r.toString(16) : v.toString()));
      } catch (e) { out.push('  [' + i + '] ERR'); }
    }
    return out.join('\n');
  }
};
