'use strict';
const FN = 0xf9b050;
let calls = 0;
let armed = false;
let armedPages = 0;
const res = [];
const hits = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }

function armAll() {
  if (armed) return 0;
  armed = true;
  const base = m_().base;
  const pages = {};
  let n = 0;
  for (let i = 0; i < res.length; i++) {
    try {
      const field = res[i].add(0x50);            // ★ 监控 +0x50 自身所在的页
      const page = field.and(ptr('0xfffffffffffff000'));
      const k = page.toString();
      if (pages[k]) continue;
      pages[k] = 1; n++;
      const tf = field;
      MemoryAccessMonitor.enable({ base: page, size: 0x1000 }, {
        onAccess: function (d) {
          try {
            if (d.operation !== 'write') return;
            const off = d.address.sub(tf).toInt32();
            if (off < 0 || off >= 4) return;
            const bt = Thread.backtrace(d.context, Backtracer.FUZZY);
            const fr = [];
            for (let k2 = 0; k2 < bt.length && k2 < 10; k2++) {
              const r = bt[k2].sub(base).toInt32();
              if (r > 0 && r < 0x3800000) fr.push(bt[k2].sub(base).toString(16));
            }
            if (hits.length < 25) hits.push('field=' + tf + ' 新值=' + tf.readS32() + '  from=' + fr.join(' <- '));
          } catch (e) { }
        }
      });
    } catch (e) { }
  }
  armedPages = n;
  return n;
}

rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try { if (this.self.add(0x50).readS32() !== 0) res.push(this.self); } catch (e) { }
        if (!armed && calls === 446) { try { armAll(); } catch (e) { } }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  armed: function () { return armed; },
  pages: function () { return armedPages; },
  count0: function () {
    let z = 0; for (let i = 0; i < res.length; i++) { try { if (res[i].add(0x50).readS32() === 0) z++; } catch (e) { } }
    return 'res=' + res.length + ' tag0=' + z;
  },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
