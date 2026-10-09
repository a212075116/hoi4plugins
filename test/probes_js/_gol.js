'use strict';
const FN = 0xf99d30;
let calls = 0, nulls = 0;
const recs = [];

function m_() { return Process.getModuleByName('hoi4.exe'); }
function cls(vt) {
  try {
    const m = m_();
    const col = vt.sub(8).readPointer();
    if (col.isNull() || col.compare(m.base) < 0 || col.compare(m.base.add(0x3800000)) >= 0) return null;
    const ptd = col.add(0xc).readU32();
    if (ptd === 0) return null;
    return m.base.add(ptd >>> 0).add(0x10).readUtf8String();
  } catch (e) { return null; }
}
function tagStr(p) {
  try {
    const s = p.readUtf8String();
    if (s && s.length > 0 && s.length <= 6) return 'str=' + s;
  } catch (e) { }
  try { return 'u32=' + p.readU32() + ' u16=' + p.readU16(); } catch (e) { return '(unreadable)'; }
}

rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        this.self = args[0];
      },
      onLeave: function (ret) {
        if (!ret.isNull()) return;
        nulls++;
        if (recs.length >= 3) return;
        try {
          const m = m_();
          const s = this.self;
          const vt = s.readPointer();
          const lines = [];
          lines.push('=== NULL #' + nulls + ' (call #' + calls + ') ===');
          lines.push('  this=' + s + '  class=' + cls(vt) + '  vtRva=' + vt.sub(m.base));
          lines.push('  this+0x50 (tag) = ' + tagStr(s.add(0x50)));
          lines.push('  bytes@this+0x50:');
          let hex = '   ';
          for (let i = 0; i < 32; i++) {
            hex += ('0' + s.add(0x50 + i).readU8().toString(16)).slice(-2) + ' ';
            if ((i + 1) % 16 === 0) { lines.push(hex); hex = '   '; }
          }
          const bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
          lines.push('  backtrace:');
          for (let i = 0; i < bt.length && i < 16; i++) {
            const rva = bt[i].sub(m.base);
            let sym = '';
            try { sym = DebugSymbol.fromAddress(bt[i]).name || ''; } catch (e) { }
            lines.push('    #' + i + ' rva=' + rva + '  ' + sym);
          }
          recs.push(lines.join('\n'));
        } catch (e) { recs.push('ERR ' + e); }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  stats: function () { return 'calls=' + calls + ' nulls=' + nulls; },
  dump: function () { return recs.length ? recs.join('\n') : '(none)'; }
};
