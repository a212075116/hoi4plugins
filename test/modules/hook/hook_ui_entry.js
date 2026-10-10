'use strict';
const RVA_UI = 0x18A1EE0;     // sub_1418A1EE0 UI 入口
function M() { return Process.getModuleByName('hoi4.exe'); }
let n = 0;
const recs = [];
rpc.exports = {
  ready: function () { return M().base.toString(); },
  install: function () {
    const m = M();
    Interceptor.attach(m.base.add(RVA_UI), {
      onEnter: function (args) {
        n++;
        if (recs.length < 6) {
          try {
            const a1 = args[0];
            const v2 = a1.add(128).readPointer();
            recs.push('[UI] #' + n + '  a1=' + a1 + '  *(a1+128)=' + v2
              + '\n        gs=' + m.base.add(0x332F260).readPointer());
          } catch (e) { recs.push('[UI] #' + n + ' err ' + e); }
        }
      }
    });
    return 'hooked ui@' + m.base.add(RVA_UI);
  },
  n: function () { return n; },
  dump: function () { return recs.length ? recs.join('\n') : '(无调用)'; }
};
