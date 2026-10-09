'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
const seen = {};
rpc.exports = {
  install: function () {
    Interceptor.attach(M().base.add(0xbb48f0), {
      onEnter: function (args) { this.tagPtr = args[0]; },
      onLeave: function (ret) {
        try {
          const tag = this.tagPtr.readS32();
          if (seen[tag] !== undefined) return;
          let found = null;
          // 扫字节找 3 字母 [A-Z][A-Z0-9]{2} 后跟 0
          const b = new Uint8Array(ret.readByteArray(0x400));
          for (let off = 0; off + 4 <= b.length; off++) {
            const c0 = b[off], c1 = b[off+1], c2 = b[off+2], c3 = b[off+3];
            const okA = c0 >= 65 && c0 <= 90;
            const okB = (c1 >= 65 && c1 <= 90) || (c1 >= 48 && c1 <= 57);
            const okC = (c2 >= 65 && c2 <= 90) || (c2 >= 48 && c2 <= 57);
            if (okA && okB && okC && c3 === 0) {
              found = String.fromCharCode(c0, c1, c2) + ' @0x' + off.toString(16);
              break;
            }
          }
          seen[tag] = found || '?';
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  get: function (t) { return seen[t] === undefined ? '(未见)' : String(seen[t]); },
  dump: function () {
    const ks = Object.keys(seen).map(Number).sort(function (a, b) { return a - b; });
    const out = [];
    for (let i = 0; i < ks.length; i++) out.push(ks[i] + '=' + seen[ks[i]]);
    return out.join('  ');
  }
};
