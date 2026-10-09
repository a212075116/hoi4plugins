'use strict';
const FN = 0xf9b050;
let calls = 0;
let armed = false;
let armedPages = 0;
const hits = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }

function watchOne(self) {
  const base = m_().base;
  const field = self.add(0x50);
  const page = field.and(ptr('0xfffffffffffff000'));
  armedPages++;
  const tf = field;
  MemoryAccessMonitor.enable({ base: page, size: 0x1000 }, {
    onAccess: function (d) {
      try {
        if (d.operation !== 'write') return;
        const off = d.address.sub(tf).toInt32();
        if (off < 0 || off >= 4) return;
        const bt = Thread.backtrace(d.context, Backtracer.FUZZY);
        const fr = [];
        for (let k = 0; k < bt.length && k < 12; k++) {
          const r = bt[k].sub(base).toInt32();
          if (r > 0 && r < 0x3800000) fr.push(bt[k].sub(base).toString(16));
        }
        if (hits.length < 30) hits.push('field=' + tf + ' 新值=' + tf.readS32() + '  from=' + fr.join(' <- '));
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
          const s = this.self;
          if (s.add(0x50).readS32() === 0) return;
          // 前 6 次调用后开始逐个装监控
          if (calls > 6 && !armed) watchOne(s);
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  pages: function () { return armedPages; },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
