'use strict';
const FN = 0xf986b0;
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
        if (recs.length >= 5) return;
        try {
          const self = args[0];       // CResistance
          const p2 = args[1];         // rdx
          const inner = self.add(8).readPointer();   // [this+8]
          const lines = [];
          lines.push('=== ComputeOccupiedTag #' + n + ' ===');
          lines.push('  this(CResistance)=' + self + '  class=' + cls(self.readPointer()));
          lines.push('  rdx=' + p2 + '  r8=' + args[2]);
          lines.push('  [this+8]=' + inner);
          if (!inner.isNull()) {
            let ic = null;
            try { ic = cls(inner.readPointer()); } catch (e) { }
            lines.push('  [this+8] class=' + ic);
            const cnt = inner.add(0xbc).readS32();
            const arr = inner.add(0xb0).readPointer();
            lines.push('  [this+8]+0xb0 arr=' + arr + '  +0xbc count=' + cnt);
            if (!arr.isNull() && cnt > 0 && cnt < 40) {
              let vals = [];
              for (let i = 0; i < Math.min(cnt, 12); i++) {
                try { vals.push(arr.add(i * 4).readS32()); } catch (e) { vals.push('?'); }
              }
              lines.push('  列表内容(前12): ' + vals.join(', '));
            }
            // 也看看 +0x484 那个上限
            try {
              lines.push('  inner+0x484=' + inner.add(0x484).readS32());
            } catch (e) { }
          }
          recs.push(lines.join('\n'));
        } catch (e) { recs.push('ERR ' + e); }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  calls: function () { return n; },
  dump: function () { return recs.join('\n'); }
};
