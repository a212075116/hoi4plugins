'use strict';
const LOGFN = 0x24c8950;
let total = 0, matched = 0;
const samples = [];

function sym(a) {
  try { return DebugSymbol.fromAddress(a).toString(); } catch (e) { return String(a); }
}

rpc.exports = {
  install: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const addr = m.base.add(LOGFN);
    Interceptor.attach(addr, {
      onEnter: function (args) {
        total++;
        try {
          const s = args[1];
          let txt = '(null)';
          if (!s.isNull()) txt = s.readUtf8String();
          if (txt && txt.indexOf('GetOccupationLaw') >= 0) {
            matched++;
            if (samples.length < 3) {
              const bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
              const lines = [];
              for (let i = 0; i < bt.length && i < 14; i++) {
                lines.push('    #' + i + ' rva=' + bt[i].sub(m.base) + '  ' + sym(bt[i]));
              }
              samples.push('=== sample ' + matched + ' ===\n' + lines.join('\n'));
            }
          } else if (total <= 3) {
            samples.push('total#' + total + ' arg2=' + txt.slice(0, 90));
          }
        } catch (e) { }
      }
    });
    return 'attached ' + addr;
  },
  stats: function () { return 'total=' + total + ' matched=' + matched; },
  dump: function () { return samples.length ? samples.join('\n') : '(no samples)'; },
  // hook 调用点所在的函数入口, 看它的符号
  caller: function (rva) { return sym(Process.getModuleByName('hoi4.exe').base.add(rva)); }
};
