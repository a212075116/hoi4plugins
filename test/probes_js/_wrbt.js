'use strict';
const WR = 0xf9b46e;
let n = 0;
const recs = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(WR), {
      onEnter: function () {
        n++;
        if (recs.length >= 3) return;
        const ctx = this.context;
        const lines = [];
        lines.push('=== #' + n + ' self=' + ctx.rbp + ' tag=' + ctx.rbp.add(0x50).readS32() + ' ===');
        try {
          const bt = Thread.backtrace(ctx, Backtracer.FUZZY);
          for (let i = 0; i < bt.length && i < 16; i++) {
            const r = bt[i].sub(m_().base);
            let sym = '';
            try { sym = DebugSymbol.fromAddress(bt[i]).name || ''; } catch (e) { }
            lines.push('    #' + i + ' rva=' + r.toString(16) + '  ' + sym);
          }
        } catch (e) { lines.push('  bt err: ' + e); }
        recs.push(lines.join('\n'));
      }
    });
    return 'hooked';
  },
  calls: function () { return n; },
  dump: function () { return recs.join('\n'); }
};
