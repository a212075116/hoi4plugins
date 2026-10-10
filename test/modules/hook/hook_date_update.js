'use strict';
const RVA_SYNC = 0x1DD370;
function M() { return Process.getModuleByName('hoi4.exe'); }
let n = 0;
const recs = [];
rpc.exports = {
  ready: function () { return M().base.toString(); },
  install: function () {
    const m = M();
    Interceptor.attach(m.base.add(RVA_SYNC), {
      onEnter: function (args) {
        n++;
        if (recs.length < 12) {
          try {
            const a1 = args[0], a2 = args[1], a3 = args[2];
            let mA1 = '?', mA2 = '?', mA3 = '?';
            try { mA1 = a1.sub(m.base).toString(); } catch (e) { }
            try { mA2 = a2.sub(m.base).toString(); } catch (e) { }
            try { mA3 = a3.sub(m.base).toString(); } catch (e) { }
            let v2 = '(unreadable)';
            try { v2 = String(a2.add(8).readS32()); } catch (e) { }
            let v1 = '(unreadable)';
            try { v1 = String(a1.add(0x468).readS32()); } catch (e) { }
            recs.push('#' + n + '  a1=' + a1 + '  a2=' + a2 + '  a3=' + a3
              + '\n        a2+8=' + v2 + '   a1+0x468=' + v1
              + '\n        (a1 rva=' + mA1 + '  a2 rva=' + mA2 + '  a3 rva=' + mA3 + ')');
          } catch (e) { }
        }
      }
    });
    return 'hooked ' + m.base.add(RVA_SYNC);
  },
  n: function () { return n; },
  dump: function () { return recs.length ? recs.join('\n') : '(无调用)'; }
};
