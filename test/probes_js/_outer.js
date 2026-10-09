'use strict';
const FN = 0x9e02c0;
let n = 0;
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
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        n++;
        if (recs.length >= 4) return;
        try {
          const s = args[0];
          const m = m_();
          const vt = s.readPointer();
          const cnt = s.add(0x63c).readS32();
          const arr = s.add(0x630).readPointer();
          const sub = s.add(0x268);
          const svt = sub.readPointer();
          const lines = [];
          lines.push('=== call #' + n + ' ===');
          lines.push('  this=' + s + '  class=' + cls(vt) + '  vtRva=' + vt.sub(m.base));
          lines.push('  this+0x630 arr=' + arr + '  this+0x63c count=' + cnt);
          lines.push('  this+0x268 class=' + cls(svt) + '  vtRva=' + svt.sub(m.base));
          lines.push('  this+0x268+0x50 (tag) u32=' + sub.add(0x50).readU32() + ' u16=' + sub.add(0x50).readU16());
          try {
            const tag = sub.add(0x50);
            const bytes = [];
            for (let i = 0; i < 16; i++) bytes.push(('0' + tag.add(i).readU8().toString(16)).slice(-2));
            lines.push('  tag bytes: ' + bytes.join(' '));
          } catch (e) { }
          const bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
          lines.push('  backtrace:');
          for (let i = 0; i < bt.length && i < 10; i++) lines.push('    #' + i + ' rva=' + bt[i].sub(m.base));
          recs.push(lines.join('\n'));
        } catch (e) { recs.push('ERR ' + e); }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  calls: function () { return n; },
  dump: function () { return recs.length ? recs.join('\n') : '(none)'; }
};
