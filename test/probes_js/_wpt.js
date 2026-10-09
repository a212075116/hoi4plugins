'use strict';
const GS = 0x332F260;
function M() { return Process.getModuleByName('hoi4.exe'); }
let hits = [];
let armed = null;
rpc.exports = {
  ready: function () { return M().base.toString(); },
  // 列出可用 API
  api: function () {
    const t = Process.getCurrentThreadId();
    return 'setHardwareWatchpoint=' + (typeof Thread.setHardwareWatchpoint) +
           '  setHardwareBreakpoint=' + (typeof Thread.setHardwareBreakpoint) +
           '  curTid=' + t;
  },
  install: function (off) {
    const gs = M().base.add(GS).readPointer();
    if (gs.isNull()) return 'CGameState NULL';
    const addr = gs.add(off);
    armed = addr;
    try {
      // 在所有线程上设硬件写断点
      const threads = Process.enumerateThreads();
      let n = 0;
      for (let i = 0; i < threads.length && n < 4; i++) {
        try {
          Thread.setHardwareWatchpoint(n, addr, 4, 'w');
          n++;
        } catch (e) { }
      }
      return 'armed on ' + addr + '  threads=' + threads.length + ' set=' + n;
    } catch (e) { return 'ERR ' + e; }
  },
  hits: function () { return hits.length ? hits.join('\n') : '(无命中)'; },
  n: function () { return hits.length; }
};
