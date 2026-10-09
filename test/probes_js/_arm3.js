'use strict';
const FN = 0xf9b050;   // SetTagAndFlag
let calls = 0;
let armed = false;
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
      const self = res[i];       // CResistance 指针
      const page = self.and(ptr('0xfffffffffffff000'));
      const k = page.toString();
      if (pages[k]) continue;
      pages[k] = 1; n++;
      const t = self;
      MemoryAccessMonitor.enable({ base: page, size: 0x1000 }, {
        onAccess: function (d) {
          try {
            if (d.operation !== 'write') return;
            const off = d.address.sub(t).toInt32();
            if (off < 0x50 || off >= 0x54) return;
            const bt = Thread.backtrace(d.context, Backtracer.FUZZY);
            const fr = [];
            for (let k = 0; k < bt.length && k < 10; k++) {
              const r = bt[k].sub(base).toInt32();
              if (r > 0 && r < 0x3800000) fr.push(bt[k].sub(base).toString(16));
            }
            if (hits.length < 25) hits.push('obj=' + t + ' off=' + off + ' 写入值=' + d.address.readS32() + '  from=' + fr.join(' <- '));
          } catch (e) { }
        }
      });
    } catch (e) { }
  }
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
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; },
  count0: function () {
    let z = 0; for (let i = 0; i < res.length; i++) { try { if (res[i].add(0x50).readS32() === 0) z++; } catch (e) { } }
    return 'res=' + res.length + ' tag0=' + z;
  }
};
