'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  gs: function () { return M().base.add(GS).readPointer().toString(); },
  // 读绝对地址附近, 看结构
  around: function (addrStr, before, after) {
    const a = ptr(addrStr);
    const out = [];
    for (let off = -before; off <= after; off += 4) {
      try {
        const o = a.add(off);
        out.push('0x' + (off < 0 ? '-' : '+') + Math.abs(off).toString(16) + '  ' + o + '  i32=' + o.readS32());
      } catch (e) { out.push('off=' + off + ' ERR'); }
    }
    return out.join('\n');
  },
  // 读它作为对象的虚表
  vtOf: function (addrStr) {
    const a = ptr(addrStr);
    try {
      const v = a.readPointer();
      return 'first qword = ' + v + '  (hoi4 rva = ' + v.sub(M().base) + ')';
    } catch (e) { return 'ERR ' + e; }
  },
  read: function (addrStr, n) {
    const a = ptr(addrStr);
    const out = [];
    for (let i = 0; i < n; i++) {
      try { out.push('+' + (i*4).toString(16) + '=' + a.add(i*4).readS32()); } catch (e) { out.push('ERR'); }
    }
    return out.join(' ');
  }
};
