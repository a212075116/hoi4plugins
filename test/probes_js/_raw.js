'use strict';
const FN = 0xf9b4b0;
let zero = 0;
const recs = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { this.res = args[0]; },
      onLeave: function (ret) {
        if (ret.toInt32() === 0) return;
        try {
          const r = this.res;
          if (r.add(0x50).readU32() !== 0) return;
          zero++;
          if (recs.length >= 4) return;
          const st = r.sub(0x268);
          const lines = [];
          lines.push('=== tag0 州 #' + zero + ' ===');
          lines.push('  CState=' + st + '  CResistance=' + r);
          lines.push('  CState 前 0x60 字节 (u32 视图):');
          for (let off = 0; off < 0x60; off += 16) {
            let h = '   +' + ('0' + off.toString(16)).slice(-2) + ':  ';
            let u = '';
            for (let k = 0; k < 16; k += 4) {
              u += st.add(off + k).readU32() + ' ';
            }
            lines.push(h + u);
          }
          lines.push('  CResistance 前 0x60 字节:');
          for (let off = 0; off < 0x60; off += 16) {
            let h = '   +' + ('0' + off.toString(16)).slice(-2) + ':  ';
            let u = '';
            for (let k = 0; k < 16; k += 4) u += r.add(off + k).readU32() + ' ';
            lines.push(h + u);
          }
          recs.push(lines.join('\n'));
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  zero: function () { return zero; },
  dump: function () { return recs.length ? recs.join('\n') : '(none)'; }
};
