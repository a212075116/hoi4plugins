'use strict';
const RVA_UI = 0x18A1EE0;
function M() { return Process.getModuleByName('hoi4.exe'); }
let lastA1 = null;
let hooked = false;
let callCount = 0;
const log = [];
rpc.exports = {
  ready: function () { return M().base.toString(); },
  // 挂一次 hook, 记下 a1 (同帧不变), 之后可以脱钩
  install: function () {
    if (hooked) return 'already, lastA1=' + lastA1;
    const m = M();
    Interceptor.attach(m.base.add(RVA_UI), {
      onEnter: function (args) {
        try { if (lastA1 === null) lastA1 = args[0].toString(); } catch (e) { }
      }
    });
    hooked = true;
    return 'hooked ui@' + m.base.add(RVA_UI);
  },
  a1: function () { return lastA1; },
  // 主动触发一次 UI 刷新
  trigger: function () {
    if (lastA1 === null) return 'no a1 yet (先 install 并等一帧)';
    const m = M();
    try {
      const fn = new NativeFunction(m.base.add(RVA_UI), 'pointer', ['pointer', 'pointer']);
      const r = fn(ptr(lastA1), ptr(0));
      callCount++;
      log.push('call #' + callCount + ' a1=' + lastA1 + ' -> ret=' + r);
      return log[log.length - 1];
    } catch (e) {
      log.push('call FAILED: ' + e);
      return log[log.length - 1];
    }
  },
  log: function () { return log.length ? log.join('\n') : '(无)'; }
};
