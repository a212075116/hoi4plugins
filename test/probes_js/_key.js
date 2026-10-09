'use strict';
const FN = 0xf986b0;
let n = 0;
const recs = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        n++;
        if (recs.length >= 6) return;
        try {
          const self = args[0];
          const st = self.add(8).readPointer();
          const lines = [];
          lines.push('=== #' + n + ' ===');
          lines.push('  CState=' + st);
          // CState 前 0x120 的 u32 视图 (找 +0xc8 等)
          for (let off = 0xa0; off < 0x120; off += 16) {
            let h = '   +' + ('00' + off.toString(16)).slice(-3) + ': ';
            let u = '';
            for (let k = 0; k < 16; k += 4) {
              try { u += st.add(off + k).readU32() + ' '; } catch (e) { u += '? '; }
            }
            lines.push(h + u);
          }
          const key = st.add(0xc8).readS32();
          const key2 = st.add(0xcc).readS32();
          const cnt = st.add(0xbc).readS32();
          const arr = st.add(0xb0).readPointer();
          lines.push('  => CState+0xc8=' + key + '   +0xcc=' + key2);
          lines.push('  => core 列表 count=' + cnt + ' arr=' + arr);
          let vals = [];
          for (let i = 0; i < Math.min(cnt, 10); i++) {
            try { vals.push(arr.add(i * 4).readS32()); } catch (e) { }
          }
          lines.push('  => 列表: ' + vals.join(', '));
          recs.push(lines.join('\n'));
        } catch (e) { recs.push('ERR ' + e); }
      }
    });
    return 'hooked';
  },
  calls: function () { return n; },
  dump: function () { return recs.join('\n'); }
};
