'use strict';
const LOGFN = 0x24c8950;
const counts = {};
let total = 0;
rpc.exports = {
  install: function () {
    const m = Process.getModuleByName('hoi4.exe');
    Interceptor.attach(m.base.add(LOGFN), {
      onEnter: function (args) {
        total++;
        try {
          const bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
          if (bt.length > 1) {
            const r = bt[1].sub(m.base).toString();
            counts[r] = (counts[r] || 0) + 1;
          }
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  stats: function () {
    const arr = [];
    for (const k in counts) arr.push([k, counts[k]]);
    arr.sort(function (a, b) { return b[1] - a[1]; });
    const top = arr.slice(0, 12).map(function (x) { return '  rva=' + x[0] + '  x' + x[1]; });
    return 'total=' + total + '\n' + top.join('\n');
  },
  clear: function () { total = 0; for (const k in counts) delete counts[k]; return 'cleared'; }
};
