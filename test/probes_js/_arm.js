'use strict';
const FN = 0xf9ae60;
let calls = 0;
let armed = false;
const hits = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }

function arm(target) {
  if (armed) return;
  armed = true;
  const page = target.and(ptr('0xfffffffffffff000'));
  const base = m_().base;
  MemoryAccessMonitor.enable({ base: page, size: 0x1000 }, {
    onAccess: function (d) {
      try {
        if (d.operation !== 'write') return;
        const off = d.address.sub(target);
        const o = off.toInt32();
        if (o < 0x50 || o >= 0x54) return;
        const bt = Thread.backtrace(d.context, Backtracer.FUZZY);
        const frames = [];
        for (let i = 0; i < bt.length && i < 10; i++) {
          const r = bt[i].sub(base);
          const ri = r.toInt32();
          if (ri > 0 && ri < 0x3800000) frames.push(r.toString(16));
        }
        if (hits.length < 30) hits.push('off=' + o + ' val=' + d.address.readS32() + '  from=' + frames.join(' <- '));
      } catch (e) { }
    }
  });
}

rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try {
          if (this.self.add(0x50).readS32() !== 0) arm(this.self);
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  armed: function () { return armed; },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
