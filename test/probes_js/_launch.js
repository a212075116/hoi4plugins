'use strict';
const hits = [];
function M() { return Process.getModuleByName('hoi4.exe'); }
function hookFn(mod, name, tag, argIdx) {
  try {
    const addr = Process.getModuleByName(mod).getExportByName(name);
    if (!addr) return;
    Interceptor.attach(addr, {
      onEnter: function (args) {
        try {
          const p = args[argIdx];
          if (p.isNull()) return;
          let hex = '';
          try { const b = new Uint8Array(p.readByteArray(200)); for (let i = 0; i < b.length; i++) { hex += ('0' + b[i].toString(16)).slice(-2); if (b[i] === 0 && b[i+1] === 0) break; } } catch (e) { }
          // 尝试两种解释
          let asW = null, asA = null;
          try { asW = p.readUtf16String(200); } catch (e) { }
          try { asA = p.readAnsiString(200); } catch (e) { }
          const bt = Thread.backtrace(this.context, Backtracer.FUZZY);
          const fr = [];
          for (let i = 0; i < bt.length && i < 10; i++) {
            try { const r = bt[i].sub(M().base).toInt32(); if (r > 0 && r < 0x3800000) fr.push('rva=' + r.toString(16)); } catch (e) { }
          }
          hits.push('### ' + tag + ' arg' + argIdx +
            '\n  W: ' + (asW ? asW.slice(0, 200) : 'null') +
            '\n  A: ' + (asA ? asA.slice(0, 200) : 'null') +
            '\n  hex: ' + hex.slice(0, 160) +
            '\n  bt: ' + fr.join(' '));
        } catch (e) { }
      }
    });
  } catch (e) { }
}
rpc.exports = {
  install: function () {
    hookFn('kernel32.dll', 'CreateProcessA', 'CreateProcessA', 1);
    hookFn('kernel32.dll', 'CreateProcessW', 'CreateProcessW', 1);
    return 'installed';
  },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; },
  n: function () { return hits.length; }
};
